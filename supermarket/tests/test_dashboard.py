from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.db.models import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from supermarket import dashboard, views
from supermarket.forms import ProductForm
from supermarket.models import (CartItem, Category, ContactMessage, DeliveryBooking, Order, OrderItem, Product,
                                StockEntry)

from .test_messages import TEST_SETTINGS

# A fixed "today" for the period maths: a Thursday, so week buckets are easy to reason about.
TODAY = date(2026, 9, 17)


def local_noon(day):
    """Midday local time on `day`, safely inside that day's window."""
    return timezone.make_aware(datetime.combine(day, datetime.min.time()) + timedelta(hours=12))


class DashboardTestCase(TestCase):
    """Shared fixtures and factories."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('staff', password='pw', is_staff=True, first_name='Ronald')
        cls.customer = User.objects.create_user('tendai', password='pw', first_name='Tendai', last_name='Moyo')
        cls.pantry = Category.objects.create(name='Pantry')
        cls.drinks = Category.objects.create(name='Drinks')
        cls.rice = cls.make_product('Rice 5kg', cls.pantry, '8.00', 20, supplier='Harare Millers')
        cls.sugar = cls.make_product('Sugar 2kg', cls.pantry, '3.50', 3)
        cls.juice = cls.make_product('Mazoe Orange', cls.drinks, '4.00', 0)
        cls.salt = cls.make_product('Salt 1kg', cls.pantry, '1.00', 50, is_available=False)

    @staticmethod
    def make_product(name, category, price, stock, **extra):
        return Product.objects.create(
            name=name, description='Test product', category=category,
            price=Decimal(price), stock_quantity=stock, **extra,
        )

    def make_order(self, status='pending', items=None, on=None, user=None, **extra):
        """An order for `items` [(product, quantity)], optionally backdated to local day `on`."""
        items = items or [(self.rice, 1)]
        order = Order.objects.create(
            user=user or self.customer, order_number=f'T{Order.objects.count() + 1:06d}', status=status,
            total_amount=sum(product.price * quantity for product, quantity in items),
            delivery_address='12 Samora Machel Ave', delivery_city=extra.pop('city', 'Harare'),
            delivery_phone='0771234567', **extra,
        )
        for product, quantity in items:
            OrderItem.objects.create(order=order, product=product, quantity=quantity, price=product.price)
        if on:
            self.backdate(order, on)
        return order

    def make_booking(self, order=None, status='pending', fee='5.00', on=None, delivery_date=None, **extra):
        booking = DeliveryBooking.objects.create(
            user=extra.pop('user', self.customer), order=order, status=status, delivery_fee=Decimal(fee),
            delivery_date=delivery_date or timezone.localdate() + timedelta(days=1),
            time_slot=extra.pop('time_slot', 'morning'), delivery_address='12 Samora Machel Ave',
            delivery_city=extra.pop('city', 'Harare'), delivery_phone=extra.pop('phone', '0771234567'), **extra,
        )
        if on:
            self.backdate(booking, on)
        return booking

    @staticmethod
    def backdate(obj, when):
        """Move created_at, which auto_now_add otherwise pins to now. Accepts a local day or a datetime."""
        if not isinstance(when, datetime):
            when = local_noon(when)
        type(obj).objects.filter(pk=obj.pk).update(created_at=when)

    @staticmethod
    def flashes(response):
        return [(message.level_tag, message.message) for message in get_messages(response.wsgi_request)]


@override_settings(**TEST_SETTINGS)
class AccessControlTests(DashboardTestCase):
    def pages(self):
        order = self.make_order()
        return [
            reverse('founder_dashboard'),
            reverse('dashboard_inventory'),
            reverse('dashboard_product_add'),
            reverse('dashboard_product_edit', args=[self.rice.id]),
            reverse('dashboard_stock_history'),
            reverse('dashboard_orders'),
            reverse('dashboard_order_detail', args=[order.id]),
            reverse('dashboard_deliveries'),
            reverse('dashboard_messages'),
        ]

    def post_only(self):
        order = self.make_order()
        booking = self.make_booking(order)
        return [
            (reverse('dashboard_restock', args=[self.rice.id]), {'quantity': 5}),
            (reverse('dashboard_adjust_stock', args=[self.rice.id]), {'new_quantity': 1}),
            (reverse('dashboard_toggle_available', args=[self.rice.id]), {}),
            (reverse('dashboard_order_status', args=[order.id]), {'status': 'cancelled'}),
            (reverse('dashboard_delivery_status', args=[booking.id]), {'status': 'delivered'}),
        ]

    def assert_sent_to_login(self, response, url):
        self.assertEqual(response.status_code, 302, url)
        self.assertTrue(response.url.startswith(reverse('login')), url)

    def test_anonymous_visitors_are_sent_to_login(self):
        for url in self.pages():
            self.assert_sent_to_login(self.client.get(url), url)

    def test_customers_are_sent_to_login(self):
        self.client.force_login(self.customer)
        for url in self.pages():
            self.assert_sent_to_login(self.client.get(url), url)

    def test_staff_can_open_every_page(self):
        self.client.force_login(self.staff)
        for url in self.pages():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertIn('nav', response.context, url)

    def test_get_to_a_post_only_view_is_not_allowed(self):
        self.client.force_login(self.staff)
        for url, _data in self.post_only():
            self.assertEqual(self.client.get(url).status_code, 405, url)

    def test_customers_cannot_post_changes(self):
        self.client.force_login(self.customer)
        for url, data in self.post_only():
            self.assert_sent_to_login(self.client.post(url, data), url)

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 20)
        self.assertTrue(self.rice.is_available)
        self.assertFalse(StockEntry.objects.exists())
        self.assertEqual(Order.objects.get().status, 'pending')
        self.assertEqual(DeliveryBooking.objects.get().status, 'pending')


class PeriodTests(TestCase):
    def test_unknown_range_falls_back_to_30_days(self):
        for key in (None, '', 'year', '30D'):
            self.assertEqual(dashboard.get_period(key, today=TODAY).key, '30d')

    def test_day_ranges_end_today_and_include_it(self):
        expected = {'7d': date(2026, 9, 11), '30d': date(2026, 8, 19), '90d': date(2026, 6, 20)}
        for key, start in expected.items():
            period = dashboard.get_period(key, today=TODAY)
            self.assertEqual((period.start, period.end), (start, TODAY), key)

    def test_twelve_months_starts_on_the_first_of_the_month_eleven_months_ago(self):
        period = dashboard.get_period('12m', today=TODAY)
        self.assertEqual(period.start, date(2025, 10, 1))
        self.assertEqual((period.previous_start, period.previous_end), (date(2024, 10, 1), date(2025, 9, 30)))

        january = dashboard.get_period('12m', today=date(2026, 1, 31))
        self.assertEqual(january.start, date(2025, 2, 1))

    def test_previous_period_is_the_same_length_immediately_before(self):
        period = dashboard.get_period('7d', today=TODAY)
        self.assertEqual((period.previous_start, period.previous_end), (date(2026, 9, 4), date(2026, 9, 10)))
        self.assertEqual(period.label, 'Last 7 days')
        self.assertEqual(period.previous_label, 'previous 7 days')

    def test_window_is_midnight_to_midnight_local_time(self):
        begin, finish = dashboard.day_window(date(2026, 9, 11), TODAY)
        # Harare is UTC+2 all year.
        self.assertEqual(begin, datetime(2026, 9, 10, 22, 0, tzinfo=dt_timezone.utc))
        self.assertEqual(finish, datetime(2026, 9, 17, 22, 0, tzinfo=dt_timezone.utc))

    def test_every_range_is_zero_filled_with_the_right_number_of_buckets(self):
        expected = {'7d': ('day', [7]), '30d': ('day', [30]), '90d': ('week', [13, 14]), '12m': ('month', [12])}
        for key, (bucket, sizes) in expected.items():
            chart = dashboard.revenue_chart(dashboard.get_period(key, today=TODAY))
            self.assertEqual(chart['bucket'], bucket)
            self.assertIn(len(chart['points']), sizes, key)
            self.assertFalse(chart['has_data'])
            for point in chart['points']:
                self.assertEqual((point['goods'], point['delivery'], point['total'], point['orders']), (0, 0, 0, 0))

    def test_ninety_days_is_13_or_14_weeks_whatever_the_weekday(self):
        for offset in range(7):
            period = dashboard.get_period('90d', today=TODAY + timedelta(days=offset))
            self.assertIn(len(dashboard.bucket_starts(period)), (13, 14))

    def test_week_buckets_start_on_monday(self):
        starts = dashboard.bucket_starts(dashboard.get_period('90d', today=TODAY))
        self.assertTrue(all(start.weekday() == 0 for start in starts))
        self.assertEqual(starts[0], date(2026, 6, 15))   # the Monday on or before 20 June
        self.assertEqual(starts[-1], date(2026, 9, 14))  # the week containing today

    def test_bucket_labels(self):
        daily = dashboard.revenue_chart(dashboard.get_period('7d', today=TODAY))['points']
        self.assertEqual((daily[0]['label'], daily[0]['start']), ('11 Sep', '2026-09-11'))
        self.assertEqual(daily[-1]['label'], '17 Sep')

        monthly = dashboard.revenue_chart(dashboard.get_period('12m', today=TODAY))['points']
        self.assertEqual((monthly[0]['label'], monthly[0]['start']), ('Oct 2025', '2025-10-01'))
        self.assertEqual(monthly[-1]['label'], 'Sep 2026')


class RevenueTests(DashboardTestCase):
    def setUp(self):
        self.period = dashboard.get_period('7d', today=TODAY)

    def test_revenue_excludes_cancelled_and_reports_delivered_separately(self):
        self.make_order('pending', [(self.rice, 2)], on=TODAY)                       # 16.00
        self.make_order('delivered', [(self.sugar, 2), (self.rice, 1)], on=TODAY)    # 15.00
        self.make_order('cancelled', [(self.rice, 10)], on=TODAY)                    # ignored
        self.make_booking(status='confirmed', fee='5.00', on=TODAY)
        self.make_booking(status='delivered', fee='10.00', on=TODAY)
        self.make_booking(status='cancelled', fee='15.00', on=TODAY)                 # ignored

        kpis = dashboard.period_kpis(self.period)

        self.assertEqual(kpis['goods_revenue'], Decimal('31.00'))
        self.assertEqual(kpis['goods_revenue_delivered'], Decimal('15.00'))
        self.assertEqual(kpis['delivery_revenue'], Decimal('15.00'))
        self.assertEqual(kpis['delivery_revenue_delivered'], Decimal('10.00'))
        self.assertEqual(kpis['total_revenue'], Decimal('46.00'))
        self.assertEqual(kpis['orders_count'], 2)
        self.assertEqual(kpis['units_sold'], 5)
        self.assertEqual(kpis['average_order_value'], Decimal('15.50'))
        self.assertEqual(kpis['deliveries_booked'], 2)

    def test_revenue_respects_the_period_window_in_local_time(self):
        inside = self.make_order(items=[(self.rice, 1)])
        outside = self.make_order(items=[(self.rice, 3)])
        # 22:00 UTC on the 10th is already the 11th in Harare; a minute earlier is not.
        self.backdate(inside, datetime(2026, 9, 10, 22, 0, tzinfo=dt_timezone.utc))
        self.backdate(outside, datetime(2026, 9, 10, 21, 59, tzinfo=dt_timezone.utc))
        self.make_booking(fee='5.00', on=TODAY - timedelta(days=7))   # the day before the window
        self.make_booking(fee='10.00', on=TODAY)

        kpis = dashboard.period_kpis(self.period)
        self.assertEqual(kpis['goods_revenue'], Decimal('8.00'))
        self.assertEqual(kpis['delivery_revenue'], Decimal('10.00'))
        self.assertEqual(kpis['units_sold'], 1)

        points = dashboard.revenue_chart(self.period)['points']
        self.assertEqual(points[0], {
            'label': '11 Sep', 'start': '2026-09-11', 'goods': 8.0, 'delivery': 0.0, 'total': 8.0, 'orders': 1,
        })
        self.assertEqual(points[-1]['delivery'], 10.0)
        self.assertEqual(sum(point['orders'] for point in points), 1)

    def test_empty_period_has_zero_kpis(self):
        kpis = dashboard.period_kpis(self.period)

        self.assertEqual(kpis['total_revenue'], Decimal('0.00'))
        self.assertEqual(kpis['average_order_value'], Decimal('0.00'))
        self.assertEqual(kpis['units_sold'], 0)
        self.assertEqual(kpis['stock_bought_units'], 0)
        self.assertEqual(kpis['stock_bought_cost'], Decimal('0.00'))
        self.assertIsNone(kpis['revenue_change_pct'])

    def test_change_against_the_previous_period(self):
        self.make_order(items=[(self.rice, 3)], on=TODAY)                         # 24.00 now
        self.assertIsNone(dashboard.period_kpis(self.period)['revenue_change_pct'])

        self.make_order(items=[(self.rice, 2)], on=TODAY - timedelta(days=7))     # 16.00 before
        self.make_order('cancelled', [(self.rice, 9)], on=TODAY - timedelta(days=8))
        kpis = dashboard.period_kpis(self.period)
        self.assertEqual(kpis['prev_total_revenue'], Decimal('16.00'))
        self.assertEqual(kpis['revenue_change_pct'], Decimal('50.0'))

        # Older than the previous period: ignored by both.
        self.make_order(items=[(self.rice, 5)], on=TODAY - timedelta(days=14))
        self.assertEqual(dashboard.period_kpis(self.period)['prev_total_revenue'], Decimal('16.00'))

    def test_a_fall_in_revenue_is_negative(self):
        self.make_order(items=[(self.rice, 1)], on=TODAY)                         # 8.00 now
        self.make_order(items=[(self.rice, 3)], on=TODAY - timedelta(days=7))     # 24.00 before

        self.assertEqual(dashboard.period_kpis(self.period)['revenue_change_pct'], Decimal('-66.7'))

    def test_weekly_and_monthly_buckets_collect_their_orders(self):
        self.make_order(items=[(self.rice, 1)], on=date(2026, 9, 14))   # Monday of this week
        self.make_order(items=[(self.rice, 1)], on=TODAY)
        self.make_order(items=[(self.rice, 1)], on=date(2026, 9, 13))   # Sunday: the week before
        self.make_booking(fee='5.00', on=date(2025, 10, 1))             # first day of the 12 months

        weekly = dashboard.revenue_chart(dashboard.get_period('90d', today=TODAY))
        self.assertTrue(weekly['has_data'])
        self.assertEqual([point['orders'] for point in weekly['points'][-2:]], [1, 2])
        self.assertEqual(weekly['points'][-1]['start'], '2026-09-14')

        monthly = dashboard.revenue_chart(dashboard.get_period('12m', today=TODAY))['points']
        self.assertEqual((monthly[0]['delivery'], monthly[0]['orders']), (5.0, 0))
        self.assertEqual((monthly[-1]['goods'], monthly[-1]['orders']), (24.0, 3))

    def test_a_period_with_only_delivery_bookings_has_data(self):
        self.make_booking(fee='5.00', on=TODAY)
        self.assertTrue(dashboard.revenue_chart(self.period)['has_data'])

    def test_top_products_are_ordered_by_revenue_with_a_share_of_the_best(self):
        self.make_order(items=[(self.rice, 5), (self.sugar, 4)], on=TODAY)       # rice 40.00, sugar 14.00
        self.make_order(items=[(self.juice, 5)], on=TODAY)                       # juice 20.00
        self.make_order('cancelled', [(self.sugar, 100)], on=TODAY)              # ignored
        self.make_order(items=[(self.salt, 500)], on=TODAY - timedelta(days=30))  # outside the period

        top = dashboard.top_products(self.period)

        self.assertEqual([row['name'] for row in top], ['Rice 5kg', 'Mazoe Orange', 'Sugar 2kg'])
        self.assertEqual([row['share_pct'] for row in top], [100, 50, 35])
        self.assertEqual(top[0], {
            'product_id': self.rice.id, 'name': 'Rice 5kg', 'units': 5,
            'revenue': Decimal('40.00'), 'share_pct': 100,
        })

    def test_top_products_uses_the_price_paid_and_stops_at_eight(self):
        for index in range(10):
            product = self.make_product(f'Item {index}', self.pantry, '1.00', 10)
            self.make_order(items=[(product, index + 1)], on=TODAY)
        # The shelf price changed after the sale; history keeps the price paid.
        Product.objects.filter(name='Item 9').update(price=Decimal('99.00'))

        top = dashboard.top_products(self.period)
        self.assertEqual(len(top), 8)
        self.assertEqual((top[0]['name'], top[0]['revenue']), ('Item 9', Decimal('10.00')))

    def test_stock_bought_counts_restocks_in_the_period(self):
        dashboard.restock_product(self.rice, 10, unit_cost=Decimal('5.25'))
        dashboard.restock_product(self.sugar, 4)                       # no cost recorded
        old = dashboard.restock_product(self.rice, 100, unit_cost=Decimal('5.00'))
        self.backdate(old, timezone.localdate() - timedelta(days=40))
        dashboard.adjust_stock(self.rice.id, 1)                        # corrections aren't purchases

        kpis = dashboard.period_kpis(dashboard.get_period('30d'))
        self.assertEqual(kpis['stock_bought_units'], 14)
        self.assertEqual(kpis['stock_bought_cost'], Decimal('52.50'))

    def test_status_breakdown_lists_every_status(self):
        self.make_order('pending', on=TODAY)
        self.make_order('pending', on=TODAY)
        self.make_order('cancelled', on=TODAY)
        self.make_order('delivered', on=TODAY - timedelta(days=20))   # outside

        rows = dashboard.status_breakdown(Order, self.period)
        self.assertEqual([row['status'] for row in rows], [status for status, _ in Order.STATUS_CHOICES])
        self.assertEqual({row['status']: row['count'] for row in rows},
                         {'pending': 2, 'processing': 0, 'shipped': 0, 'delivered': 0, 'cancelled': 1})
        self.assertEqual(rows[0]['label'], 'Pending')

        deliveries = dashboard.status_breakdown(DeliveryBooking, self.period)
        self.assertEqual(len(deliveries), len(DeliveryBooking.STATUS_CHOICES))
        self.assertTrue(all(row['count'] == 0 for row in deliveries))


@override_settings(**TEST_SETTINGS)
class OverviewPageTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.staff)

    def test_context_follows_the_contract(self):
        order = self.make_order('pending', [(self.rice, 2)])
        self.make_booking(order, fee='5.00')
        ContactMessage.objects.create(name='Rudo', subject='Hours', message='Open on Sunday?')

        response = self.client.get(reverse('founder_dashboard'))
        context = response.context

        self.assertTemplateUsed(response, 'supermarket/dashboard/overview.html')
        self.assertEqual((context['range_key'], context['range_label']), ('30d', 'Last 30 days'))
        self.assertEqual(context['previous_label'], 'previous 30 days')
        self.assertEqual(context['range_options'][0], ('7d', '7 days'))
        self.assertEqual(context['period_end'], timezone.localdate())
        self.assertEqual(context['period_start'], timezone.localdate() - timedelta(days=29))
        self.assertEqual(set(context['kpis']), {
            'total_revenue', 'prev_total_revenue', 'revenue_change_pct', 'goods_revenue',
            'goods_revenue_delivered', 'delivery_revenue', 'delivery_revenue_delivered', 'orders_count',
            'units_sold', 'average_order_value', 'deliveries_booked', 'stock_bought_units', 'stock_bought_cost',
        })
        self.assertEqual(context['kpis']['total_revenue'], Decimal('21.00'))
        self.assertEqual(len(context['chart']['points']), 30)
        self.assertTrue(context['chart']['has_data'])
        self.assertEqual(context['top_products'][0]['name'], 'Rice 5kg')
        self.assertEqual(list(context['recent_orders']), [order])
        self.assertEqual([message.subject for message in context['awaiting_messages']], ['Hours'])
        self.assertEqual(context['nav'], {
            'active': 'overview', 'out_of_stock': 1, 'low_stock': 1,
            'pending_orders': 1, 'pending_deliveries': 1, 'open_messages': 1,
        })
        self.assertContains(response, 'Rice 5kg')

    def test_range_parameter(self):
        self.assertEqual(self.client.get(reverse('founder_dashboard'), {'range': '12m'}).context['range_key'], '12m')
        self.assertEqual(self.client.get(reverse('founder_dashboard'), {'range': 'bogus'}).context['range_key'], '30d')

    def test_inventory_summary_and_stock_alerts(self):
        self.make_product('Bread', self.pantry, '1.50', 0)

        context = self.client.get(reverse('founder_dashboard')).context

        self.assertEqual(context['inventory'], {
            'total': 5, 'in_stock': 1, 'low_stock': 1, 'out_of_stock': 2, 'hidden': 1,
            # rice 20 x 8.00 + sugar 3 x 3.50; hidden salt is left out.
            'retail_value': Decimal('170.50'),
        })
        # Lowest stock first, then by name; hidden and well-stocked products never alert.
        self.assertEqual([product.name for product in context['stock_alerts']],
                         ['Bread', 'Mazoe Orange', 'Sugar 2kg'])

    def test_upcoming_deliveries_are_active_future_bookings_in_delivery_order(self):
        today = timezone.localdate()
        evening = self.make_booking(delivery_date=today, time_slot='evening', status='confirmed')
        morning = self.make_booking(delivery_date=today, time_slot='morning', status='in_transit')
        tomorrow = self.make_booking(delivery_date=today + timedelta(days=1), time_slot='afternoon')
        self.make_booking(delivery_date=today - timedelta(days=1))                      # past
        self.make_booking(delivery_date=today, status='delivered')                      # done
        self.make_booking(delivery_date=today + timedelta(days=2), status='cancelled')  # cancelled

        context = self.client.get(reverse('founder_dashboard')).context
        self.assertEqual(list(context['upcoming_deliveries']), [morning, evening, tomorrow])


@override_settings(**TEST_SETTINGS)
class InventoryPageTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.staff)

    def names(self, **params):
        response = self.client.get(reverse('dashboard_inventory'), params)
        return [product.name for product in response.context['products']]

    def test_stock_state(self):
        self.assertEqual([p.stock_state for p in (self.rice, self.sugar, self.juice, self.salt)],
                         ['in', 'low', 'out', 'hidden'])
        self.assertEqual(self.make_product('Edge', self.pantry, '1', Product.LOW_STOCK_THRESHOLD).stock_state, 'low')
        self.assertEqual(self.make_product('Over', self.pantry, '1', Product.LOW_STOCK_THRESHOLD + 1).stock_state, 'in')
        # Hidden wins over out of stock and over low stock.
        self.assertEqual(self.make_product('Gone', self.pantry, '1', 0, is_available=False).stock_state, 'hidden')
        self.assertEqual(self.make_product('Going', self.pantry, '1', 3, is_available=False).stock_state, 'hidden')

    def test_default_view_lists_everything_lowest_stock_first(self):
        response = self.client.get(reverse('dashboard_inventory'))

        self.assertEqual([p.name for p in response.context['products']],
                         ['Mazoe Orange', 'Sugar 2kg', 'Rice 5kg', 'Salt 1kg'])
        self.assertEqual(response.context['active_filter'], 'all')
        self.assertEqual(response.context['sort'], 'stock_low')
        self.assertEqual(response.context['counts'], {'all': 4, 'in': 1, 'low': 1, 'out': 1, 'hidden': 1})
        self.assertEqual(response.context['inventory']['total'], 4)
        self.assertEqual(response.context['selected_category'], '')
        self.assertContains(response, 'Mazoe Orange')

    def test_stock_filters(self):
        self.assertEqual(self.names(filter='in'), ['Rice 5kg'])
        self.assertEqual(self.names(filter='low'), ['Sugar 2kg'])
        self.assertEqual(self.names(filter='out'), ['Mazoe Orange'])
        self.assertEqual(self.names(filter='hidden'), ['Salt 1kg'])
        self.assertEqual(len(self.names(filter='nonsense')), 4)

    def test_search_matches_name_supplier_and_category(self):
        self.assertEqual(self.names(search='mazoe'), ['Mazoe Orange'])
        self.assertEqual(self.names(search='millers'), ['Rice 5kg'])
        self.assertEqual(self.names(search='drinks'), ['Mazoe Orange'])
        self.assertEqual(self.names(search='zzz'), [])

    def test_counts_follow_the_search_and_category(self):
        response = self.client.get(reverse('dashboard_inventory'), {'category': self.pantry.id, 'filter': 'low'})

        self.assertEqual(response.context['counts'], {'all': 3, 'in': 1, 'low': 1, 'out': 0, 'hidden': 1})
        self.assertEqual(response.context['selected_category'], str(self.pantry.id))
        # The summary tiles always describe the whole catalogue.
        self.assertEqual(response.context['inventory']['total'], 4)

    def test_bad_category_is_ignored(self):
        # A superscript two passes str.isdigit() but int() and the id field
        # reject it; thirty digits overflow SQLite's integer. Both were a 500.
        for value in ('abc', '\u00b2', '9' * 30, '0', '-1', ''):
            with self.subTest(category=value):
                response = self.client.get(reverse('dashboard_inventory'), {'category': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['selected_category'], '')
                self.assertEqual(len(response.context['products']), 4)

                # The shop's own category filter follows the same rule, without a login.
                shop = Client().get(reverse('product_list'), {'category': value})
                self.assertEqual(shop.status_code, 200)
                self.assertIsNone(shop.context['selected_category'])
                self.assertEqual(len(shop.context['products']), 3)

    def test_a_real_category_still_filters_the_shop(self):
        shop = Client().get(reverse('product_list'), {'category': self.drinks.id})
        self.assertEqual(shop.context['selected_category'], str(self.drinks.id))
        self.assertEqual([p.name for p in shop.context['products']], ['Mazoe Orange'])

    def test_sorting(self):
        self.assertEqual(self.names(sort='name'), ['Mazoe Orange', 'Rice 5kg', 'Salt 1kg', 'Sugar 2kg'])
        self.assertEqual(self.names(sort='stock_high')[0], 'Salt 1kg')
        self.assertEqual(self.client.get(reverse('dashboard_inventory'), {'sort': 'x'}).context['sort'], 'stock_low')

    def test_sorting_newest_first(self):
        # The fixtures share one creation instant, so each product gets its own day.
        for age, product in enumerate((self.sugar, self.salt, self.juice, self.rice)):
            self.backdate(product, timezone.localdate() - timedelta(days=age))

        response = self.client.get(reverse('dashboard_inventory'), {'sort': 'newest'})

        self.assertEqual(response.context['sort'], 'newest')
        self.assertEqual([p.name for p in response.context['products']],
                         ['Sugar 2kg', 'Salt 1kg', 'Mazoe Orange', 'Rice 5kg'])

    def test_units_sold_is_all_time_and_ignores_cancelled_orders(self):
        self.make_order('delivered', [(self.rice, 2)], on=timezone.localdate() - timedelta(days=400))
        self.make_order('pending', [(self.rice, 3)])
        self.make_order('cancelled', [(self.rice, 50)])

        products = {p.name: p for p in self.client.get(reverse('dashboard_inventory')).context['products']}
        self.assertEqual(products['Rice 5kg'].units_sold, 5)
        self.assertEqual(products['Sugar 2kg'].units_sold, 0)

    def test_pagination(self):
        for index in range(25):
            self.make_product(f'Extra {index:02d}', self.pantry, '1.00', 10)

        page = self.client.get(reverse('dashboard_inventory')).context['products']
        self.assertEqual((len(page), page.paginator.count, page.paginator.num_pages), (24, 29, 2))


@override_settings(**TEST_SETTINGS)
class StockChangeTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.staff)

    def product_form_data(self, **overrides):
        data = {
            'name': 'Cooking Oil 2L', 'description': 'Sunflower oil', 'category': self.pantry.id,
            'price': '4.75', 'image': '', 'supplier': 'Olivine', 'is_available': 'on', 'opening_stock': '12',
        }
        data.update(overrides)
        return data

    def test_restock_adds_to_the_stock_and_logs_it(self):
        response = self.client.post(reverse('dashboard_restock', args=[self.rice.id]), {
            'quantity': '15', 'unit_cost': '5.20', 'supplier': '', 'note': 'Invoice 881',
        })

        self.assertRedirects(response, reverse('dashboard_inventory'))
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 35)
        entry = StockEntry.objects.get()
        self.assertEqual((entry.product, entry.kind, entry.quantity, entry.stock_after), (self.rice, 'restock', 15, 35))
        self.assertEqual((entry.unit_cost, entry.total_cost), (Decimal('5.20'), Decimal('78.00')))
        # A blank supplier falls back to the product's usual one.
        self.assertEqual((entry.supplier, entry.note, entry.created_by), ('Harare Millers', 'Invoice 881', self.staff))
        self.assertEqual(self.flashes(response)[0][0], 'success')

    def test_quick_restock_needs_only_a_quantity(self):
        self.client.post(reverse('dashboard_restock', args=[self.juice.id]), {'quantity': '6'})

        self.juice.refresh_from_db()
        self.assertEqual(self.juice.stock_quantity, 6)
        entry = StockEntry.objects.get()
        self.assertIsNone(entry.unit_cost)
        self.assertIsNone(entry.total_cost)

    def test_invalid_restock_changes_nothing(self):
        for quantity in ('0', '-4', 'lots', ''):
            response = self.client.post(reverse('dashboard_restock', args=[self.rice.id]), {'quantity': quantity})
            self.assertEqual(self.flashes(response)[-1][0], 'error', quantity)

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 20)
        self.assertFalse(StockEntry.objects.exists())

    def test_adjust_logs_the_difference(self):
        response = self.client.post(reverse('dashboard_adjust_stock', args=[self.rice.id]),
                                    {'new_quantity': '17', 'note': 'Three bags torn'})

        self.assertRedirects(response, reverse('dashboard_inventory'))
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 17)
        entry = StockEntry.objects.get()
        self.assertEqual((entry.kind, entry.quantity, entry.stock_after), ('adjustment', -3, 17))
        self.assertEqual((entry.note, entry.created_by), ('Three bags torn', self.staff))

    def test_adjust_upwards_and_to_zero(self):
        self.client.post(reverse('dashboard_adjust_stock', args=[self.juice.id]), {'new_quantity': '4'})
        self.client.post(reverse('dashboard_adjust_stock', args=[self.sugar.id]), {'new_quantity': '0'})

        self.assertEqual(StockEntry.objects.get(product=self.juice).quantity, 4)
        self.assertEqual(StockEntry.objects.get(product=self.sugar).quantity, -3)
        self.sugar.refresh_from_db()
        self.assertEqual(self.sugar.stock_quantity, 0)

    def test_adjust_to_the_same_level_does_nothing(self):
        response = self.client.post(reverse('dashboard_adjust_stock', args=[self.rice.id]), {'new_quantity': '20'})

        self.assertFalse(StockEntry.objects.exists())
        self.assertEqual(self.flashes(response)[0][0], 'info')

    def test_invalid_adjust_changes_nothing(self):
        for quantity in ('-1', '', 'abc'):
            response = self.client.post(reverse('dashboard_adjust_stock', args=[self.rice.id]),
                                        {'new_quantity': quantity})
            self.assertEqual(self.flashes(response)[-1][0], 'error', quantity)

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 20)
        self.assertFalse(StockEntry.objects.exists())

    def test_next_is_followed_only_within_the_site(self):
        edit_url = reverse('dashboard_product_edit', args=[self.rice.id])
        inventory_url = reverse('dashboard_inventory') + '?filter=low&page=2'

        for safe in (edit_url, inventory_url):
            response = self.client.post(reverse('dashboard_restock', args=[self.rice.id]),
                                        {'quantity': '1', 'next': safe})
            self.assertRedirects(response, safe, fetch_redirect_response=False)

        for unsafe in ('https://evil.example/steal', '//evil.example/steal', 'javascript:alert(1)'):
            for name, data in (('dashboard_restock', {'quantity': '1'}), ('dashboard_adjust_stock', {'new_quantity': '2'})):
                response = self.client.post(reverse(name, args=[self.rice.id]), {**data, 'next': unsafe})
                self.assertRedirects(response, reverse('dashboard_inventory'), fetch_redirect_response=False)

    def test_status_views_reject_an_open_redirect_too(self):
        order = self.make_order()
        booking = self.make_booking(order)

        response = self.client.post(reverse('dashboard_order_status', args=[order.id]),
                                    {'status': 'processing', 'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('dashboard_orders'), fetch_redirect_response=False)

        response = self.client.post(reverse('dashboard_delivery_status', args=[booking.id]),
                                    {'status': 'confirmed', 'next': '//evil.example/'})
        self.assertRedirects(response, reverse('dashboard_deliveries'), fetch_redirect_response=False)

        detail = reverse('dashboard_order_detail', args=[order.id])
        response = self.client.post(reverse('dashboard_order_status', args=[order.id]),
                                    {'status': 'shipped', 'next': detail})
        self.assertRedirects(response, detail, fetch_redirect_response=False)

    def test_add_product_with_opening_stock_logs_a_restock(self):
        response = self.client.post(reverse('dashboard_product_add'), self.product_form_data())

        self.assertRedirects(response, reverse('dashboard_inventory'))
        product = Product.objects.get(name='Cooking Oil 2L')
        self.assertEqual((product.stock_quantity, product.price, product.is_available), (12, Decimal('4.75'), True))
        self.assertFalse(product.is_local_product)
        entry = StockEntry.objects.get()
        self.assertEqual((entry.product, entry.kind, entry.quantity, entry.stock_after), (product, 'restock', 12, 12))
        self.assertEqual((entry.note, entry.supplier, entry.created_by), ('Opening stock', 'Olivine', self.staff))

    def test_add_product_without_opening_stock_logs_nothing(self):
        for opening_stock in ('0', ''):
            self.client.post(reverse('dashboard_product_add'),
                             self.product_form_data(name=f'Oil {opening_stock or "blank"}', opening_stock=opening_stock))

        self.assertEqual(Product.objects.filter(name__startswith='Oil', stock_quantity=0).count(), 2)
        self.assertFalse(StockEntry.objects.exists())

    def test_add_product_errors_are_shown(self):
        response = self.client.post(reverse('dashboard_product_add'),
                                    self.product_form_data(name='', price='-1', opening_stock='-5'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['form'].errors), {'name', 'price', 'opening_stock'})
        self.assertIsNone(response.context['product'])
        self.assertFalse(Product.objects.filter(supplier='Olivine').exists())

    def test_edit_saves_details_but_never_the_stock(self):
        url = reverse('dashboard_product_edit', args=[self.rice.id])
        response = self.client.post(url, self.product_form_data(name='Rice 10kg', price='15.00', opening_stock='999',
                                                                stock_quantity='999'))

        self.assertRedirects(response, url)
        self.rice.refresh_from_db()
        self.assertEqual((self.rice.name, self.rice.price, self.rice.stock_quantity), ('Rice 10kg', Decimal('15.00'), 20))
        self.assertFalse(StockEntry.objects.exists())

    def test_edit_page_context(self):
        for quantity in (1, 2, 3):
            dashboard.restock_product(self.rice, quantity)
        dashboard.restock_product(self.sugar, 9)

        response = self.client.get(reverse('dashboard_product_edit', args=[self.rice.id]))

        self.assertEqual(response.context['product'], self.rice)
        self.assertNotIn('opening_stock', response.context['form'].fields)
        self.assertIn('opening_stock', ProductForm().fields)
        self.assertEqual(response.context['adjust_form']['new_quantity'].value(), 26)
        self.assertEqual([entry.quantity for entry in response.context['entries']], [3, 2, 1])
        self.assertIn('restock_form', response.context)

    def test_edit_page_shows_only_the_last_ten_entries(self):
        for _ in range(12):
            dashboard.restock_product(self.rice, 1)

        response = self.client.get(reverse('dashboard_product_edit', args=[self.rice.id]))
        self.assertEqual(len(response.context['entries']), 10)

    def test_toggle_availability(self):
        url = reverse('dashboard_toggle_available', args=[self.rice.id])

        self.assertEqual(self.client.post(url).json(), {'success': True, 'is_available': False})
        self.rice.refresh_from_db()
        self.assertFalse(self.rice.is_available)
        # Hidden products disappear from the shop but keep their stock.
        self.assertEqual(self.client.get(reverse('product_detail', args=[self.rice.id])).status_code, 404)
        self.assertEqual(self.rice.stock_quantity, 20)

        self.assertEqual(self.client.post(url).json(), {'success': True, 'is_available': True})

    def test_toggle_availability_says_what_happened_on_the_reloaded_page(self):
        url = reverse('dashboard_toggle_available', args=[self.rice.id])
        in_stock_tab = (reverse('dashboard_inventory'), {'filter': 'in'})

        # main.js reloads the page after the JSON call. Rice has just left the
        # "In stock" tab, so the toast is all that names it.
        self.client.post(url)
        page = self.client.get(*in_stock_tab)
        self.assertEqual(list(page.context['products']), [])
        self.assertEqual([(m.level_tag, m.message) for m in page.context['messages']],
                         [('success', 'Rice 5kg is now hidden from the shop. '
                                      'Find it under the Hidden tab to show it again.')])

        self.client.post(url)
        page = self.client.get(*in_stock_tab)
        self.assertEqual([(m.level_tag, m.message) for m in page.context['messages']],
                         [('success', 'Rice 5kg is showing in the shop again.')])

    def test_a_sold_product_cannot_be_deleted(self):
        self.make_order(items=[(self.rice, 1)])

        with self.assertRaises(ProtectedError):
            self.rice.delete()

    def test_stock_history_filters_and_totals(self):
        dashboard.restock_product(self.rice, 10, unit_cost=Decimal('5.00'))
        dashboard.restock_product(self.rice, 5)
        dashboard.restock_product(self.sugar, 4, unit_cost=Decimal('2.00'))
        dashboard.adjust_stock(self.rice.id, 30)

        context = self.client.get(reverse('dashboard_stock_history')).context
        self.assertEqual(context['counts'], {'all': 4, 'restock': 3, 'adjustment': 1})
        self.assertEqual(context['totals'], {'units_in': 19, 'cost': Decimal('58.00')})
        self.assertEqual((context['active_kind'], context['product']), ('all', None))
        self.assertEqual(len(context['entries']), 4)

        context = self.client.get(reverse('dashboard_stock_history'), {'product': self.rice.id}).context
        self.assertEqual(context['product'], self.rice)
        self.assertEqual(context['counts'], {'all': 3, 'restock': 2, 'adjustment': 1})
        self.assertEqual(context['totals'], {'units_in': 15, 'cost': Decimal('50.00')})

        context = self.client.get(reverse('dashboard_stock_history'),
                                  {'product': self.rice.id, 'kind': 'adjustment'}).context
        self.assertEqual(context['active_kind'], 'adjustment')
        self.assertEqual([entry.quantity for entry in context['entries']], [-5])
        self.assertEqual(context['totals'], {'units_in': 0, 'cost': Decimal('0.00')})

        # Including the two values str.isdigit() lets through but the id field can't take.
        for value in ('x', '\u00b2', '9' * 30):
            context = self.client.get(reverse('dashboard_stock_history'), {'product': value, 'kind': 'y'}).context
            self.assertEqual((context['active_kind'], context['product']), ('all', None), value)
            self.assertEqual(len(context['entries']), 4)


@override_settings(**TEST_SETTINGS)
class AdminStockTests(DashboardTestCase):
    """Django admin writes no stock log, so it must not be able to move stock."""

    def setUp(self):
        self.client.force_login(User.objects.create_superuser('root', password='pw'))

    def product_form(self, **changes):
        return {'name': 'Rice 5kg', 'description': 'Test product', 'category': self.pantry.id, 'price': '8.00',
                'is_available': 'on', 'supplier': 'Harare Millers', **changes}

    def test_the_product_list_edits_price_but_not_stock(self):
        url = reverse('admin:supermarket_product_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'name="form-0-price"')
        self.assertNotRegex(response.content.decode(), r'name="form-\d+-stock_quantity"')

        forms = response.context['cl'].formset.forms
        data = {'form-TOTAL_FORMS': len(forms), 'form-INITIAL_FORMS': len(forms), '_save': 'Save'}
        for index, form in enumerate(forms):
            data.update({f'form-{index}-id': form.instance.pk, f'form-{index}-price': '9.99',
                         f'form-{index}-stock_quantity': 99})
        self.assertEqual(self.client.post(url, data).status_code, 302)

        # The prices prove the edit was accepted; the posted stock was ignored.
        self.assertEqual(set(Product.objects.values_list('price', flat=True)), {Decimal('9.99')})
        self.assertEqual(sorted(Product.objects.values_list('stock_quantity', flat=True)), [0, 3, 20, 50])
        self.assertFalse(StockEntry.objects.exists())

    def test_the_product_page_shows_stock_read_only_and_points_to_the_dashboard(self):
        url = reverse('admin:supermarket_product_change', args=[self.rice.id])
        response = self.client.get(url)
        self.assertNotContains(response, 'name="stock_quantity"')
        self.assertContains(response, f'href="{reverse("dashboard_product_edit", args=[self.rice.id])}#restock"')

        response = self.client.post(url, self.product_form(name='Rice 10kg', stock_quantity=99))

        self.assertEqual(response.status_code, 302)
        self.rice.refresh_from_db()
        self.assertEqual((self.rice.name, self.rice.stock_quantity), ('Rice 10kg', 20))

    def test_a_product_can_still_be_added_and_starts_with_no_stock(self):
        url = reverse('admin:supermarket_product_add')
        self.assertContains(self.client.get(url), 'Starts at 0')

        response = self.client.post(url, self.product_form(name='Beans 500g', stock_quantity=40))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Product.objects.get(name='Beans 500g').stock_quantity, 0)


@override_settings(**TEST_SETTINGS)
class OrderStatusTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.staff)

    def set_status(self, order, status):
        return self.client.post(reverse('dashboard_order_status', args=[order.id]), {'status': status})

    def test_cancelling_returns_stock_exactly_once_and_cancels_the_delivery(self):
        order = self.make_order('processing', [(self.rice, 4), (self.sugar, 2)])
        booking = self.make_booking(order, status='confirmed')
        done = self.make_booking(order, status='delivered')

        first = self.set_status(order, 'cancelled')
        second = self.set_status(order, 'cancelled')

        self.rice.refresh_from_db()
        self.sugar.refresh_from_db()
        self.assertEqual((self.rice.stock_quantity, self.sugar.stock_quantity), (24, 5))
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        booking.refresh_from_db()
        self.assertEqual((booking.status, booking.cancellation_reason, booking.cancellation_notes),
                         ('cancelled', 'other', 'Order cancelled by staff'))
        self.assertIsNotNone(booking.cancelled_at)
        done.refresh_from_db()
        self.assertEqual(done.status, 'delivered')
        self.assertEqual(self.flashes(first)[0][0], 'success')
        self.assertEqual(self.flashes(second)[-1][0], 'info')
        # Returned stock isn't a purchase or a correction.
        self.assertFalse(StockEntry.objects.exists())

    def test_the_cancel_message_says_only_what_happened_to_the_delivery(self):
        no_booking = self.make_order('pending')
        open_booking = self.make_order('pending')
        self.make_booking(open_booking, status='confirmed')
        delivered = self.make_order('delivered')
        self.make_booking(delivered, status='delivered')

        def message_for(order):
            level, message = self.flashes(self.set_status(order, 'cancelled'))[-1]
            self.assertEqual(level, 'success')
            return message

        number = no_booking.order_number
        self.assertEqual(message_for(no_booking), f'Order #{number} cancelled. Its items were returned to stock.')
        self.assertTrue(message_for(open_booking).endswith('returned to stock. Its delivery booking was cancelled too.'))
        # The booking stays delivered and its fee still counts, so the toast must not claim otherwise.
        kept = message_for(delivered)
        self.assertIn('stays delivered', kept)
        self.assertNotIn('was cancelled', kept)
        self.assertEqual(DeliveryBooking.objects.get(order=delivered).status, 'delivered')

    def test_cancel_guard_holds_even_with_a_stale_order_object(self):
        order = self.make_order('pending', [(self.rice, 4)])
        stale = Order.objects.get(pk=order.pk)

        self.assertTrue(dashboard.cancel_order(order))
        self.assertFalse(dashboard.cancel_order(stale))
        self.assertEqual(dashboard.change_order_status(stale, 'cancelled')[0], 'error')

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 24)

    def test_a_cancelled_order_is_final(self):
        order = self.make_order('cancelled', [(self.rice, 4)])

        for status in ('pending', 'processing', 'shipped', 'delivered'):
            response = self.set_status(order, status)
            self.assertEqual(self.flashes(response)[-1][0], 'error', status)

        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 20)

    def test_a_stale_page_cannot_revive_an_order_cancelled_elsewhere(self):
        order = self.make_order('pending')
        stale = Order.objects.get(pk=order.pk)
        dashboard.cancel_order(order)

        self.assertEqual(dashboard.change_order_status(stale, 'shipped')[0], 'error')
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'cancelled')

    def test_other_statuses_move_in_either_direction(self):
        order = self.make_order('pending')

        for status in ('processing', 'shipped', 'delivered', 'processing', 'pending'):
            response = self.set_status(order, status)
            order.refresh_from_db()
            self.assertEqual(order.status, status)
            self.assertEqual(self.flashes(response)[-1][0], 'success')

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 20)

    def test_unknown_and_unchanged_statuses_do_nothing(self):
        order = self.make_order('processing')

        for status, level in (('teleported', 'error'), ('', 'error'), ('processing', 'info')):
            response = self.set_status(order, status)
            self.assertRedirects(response, reverse('dashboard_orders'))
            self.assertEqual(self.flashes(response)[-1][0], level, status)
            order.refresh_from_db()
            self.assertEqual(order.status, 'processing')

    def test_orders_page_filters_counts_and_search(self):
        # A username unlike the name, so each search field has to earn its own match.
        other = User.objects.create_user('rdube88', password='pw', first_name='Rudo', last_name='Chuma')
        first = self.make_order('pending', [(self.rice, 2), (self.sugar, 1)])
        second = self.make_order('delivered', user=other, city='Bulawayo')
        self.make_order('cancelled')

        context = self.client.get(reverse('dashboard_orders')).context
        self.assertEqual(context['counts'],
                         {'all': 3, 'pending': 1, 'processing': 0, 'shipped': 0, 'delivered': 1, 'cancelled': 1})
        self.assertEqual(context['active_status'], 'all')
        self.assertEqual(context['status_choices'], Order.STATUS_CHOICES)
        self.assertEqual({order.pk: order.item_count for order in context['orders']}[first.pk], 3)

        context = self.client.get(reverse('dashboard_orders'), {'status': 'delivered'}).context
        self.assertEqual(list(context['orders']), [second])

        for query in ('rdube88', 'RUDO', 'chuma', 'bulawayo', second.order_number, f'#{second.order_number}'):
            context = self.client.get(reverse('dashboard_orders'), {'search': query}).context
            self.assertEqual(list(context['orders']), [second], query)
            self.assertEqual(context['counts']['all'], 1)
        self.assertEqual(self.client.get(reverse('dashboard_orders'), {'status': 'x'}).context['active_status'], 'all')

    def test_order_detail_context(self):
        order = self.make_order('pending', [(self.rice, 2)])
        self.make_booking(order, status='cancelled')
        newest = self.make_booking(order, status='confirmed')

        response = self.client.get(reverse('dashboard_order_detail', args=[order.id]))

        self.assertEqual(response.context['order'], order)
        self.assertEqual([item.product for item in response.context['items']], [self.rice])
        self.assertEqual(response.context['delivery'], newest)
        self.assertTrue(response.context['can_change_status'])
        self.assertContains(response, 'Rice 5kg')

        order.status = 'cancelled'
        order.save()
        response = self.client.get(reverse('dashboard_order_detail', args=[order.id]))
        self.assertFalse(response.context['can_change_status'])

        unbooked = self.make_order()
        self.assertIsNone(self.client.get(reverse('dashboard_order_detail', args=[unbooked.id])).context['delivery'])
        self.assertEqual(self.client.get(reverse('dashboard_order_detail', args=[99999])).status_code, 404)


@override_settings(**TEST_SETTINGS)
class DeliveryStatusTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.staff)

    def set_status(self, booking, status):
        return self.client.post(reverse('dashboard_delivery_status', args=[booking.id]), {'status': status})

    def test_in_transit_marks_the_order_shipped(self):
        for order_status in ('pending', 'processing'):
            order = self.make_order(order_status)
            booking = self.make_booking(order, status='confirmed')

            response = self.set_status(booking, 'in_transit')

            order.refresh_from_db()
            booking.refresh_from_db()
            self.assertEqual((booking.status, order.status), ('in_transit', 'shipped'))
            level, message = self.flashes(response)[-1]
            self.assertEqual(level, 'success')
            self.assertIn(order.order_number, message)

    def test_in_transit_never_moves_an_order_backwards(self):
        order = self.make_order('delivered')
        booking = self.make_booking(order, status='confirmed')

        response = self.set_status(booking, 'in_transit')

        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')
        self.assertNotIn(order.order_number, self.flashes(response)[-1][1])

    def test_delivered_marks_the_order_delivered(self):
        for order_status in ('pending', 'processing', 'shipped'):
            order = self.make_order(order_status)
            booking = self.make_booking(order, status='in_transit')

            response = self.set_status(booking, 'delivered')

            order.refresh_from_db()
            self.assertEqual(order.status, 'delivered', order_status)
            self.assertIn(order.order_number, self.flashes(response)[-1][1])

    def test_a_cancelled_order_is_never_resurrected(self):
        order = self.make_order('cancelled')
        booking = self.make_booking(order, status='confirmed')

        for status in ('in_transit', 'delivered'):
            self.set_status(booking, status)
            order.refresh_from_db()
            self.assertEqual(order.status, 'cancelled')

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'delivered')

    def test_other_changes_leave_the_order_alone(self):
        order = self.make_order('pending')
        booking = self.make_booking(order, status='pending')

        self.set_status(booking, 'confirmed')
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

        self.set_status(booking, 'cancelled')
        order.refresh_from_db()
        booking.refresh_from_db()
        self.assertEqual(order.status, 'pending')
        self.assertEqual((booking.status, booking.cancellation_reason, booking.cancellation_notes),
                         ('cancelled', 'other', 'Cancelled by staff'))
        self.assertIsNotNone(booking.cancelled_at)

    def test_a_booking_without_an_order_can_be_updated(self):
        booking = self.make_booking(status='confirmed')

        response = self.set_status(booking, 'delivered')

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'delivered')
        self.assertEqual(self.flashes(response)[-1][0], 'success')

    def test_a_cancelled_booking_is_final(self):
        order = self.make_order('pending')
        booking = self.make_booking(order, status='cancelled')

        for status in ('pending', 'confirmed', 'in_transit', 'delivered'):
            response = self.set_status(booking, status)
            self.assertEqual(self.flashes(response)[-1][0], 'error', status)

        booking.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual((booking.status, order.status), ('cancelled', 'pending'))

    def test_unknown_and_unchanged_statuses_do_nothing(self):
        booking = self.make_booking(status='confirmed')

        for status, level in (('shipped', 'error'), ('', 'error'), ('confirmed', 'info')):
            response = self.set_status(booking, status)
            self.assertRedirects(response, reverse('dashboard_deliveries'))
            self.assertEqual(self.flashes(response)[-1][0], level, status)
            booking.refresh_from_db()
            self.assertEqual(booking.status, 'confirmed')

    def test_missing_booking_is_a_404(self):
        response = self.client.post(reverse('dashboard_delivery_status', args=[99999]), {'status': 'delivered'})
        self.assertEqual(response.status_code, 404)

    def test_deliveries_page_filters_counts_and_search(self):
        today = timezone.localdate()
        # A username unlike the name and a phone of its own, so each search field has to earn its match.
        other = User.objects.create_user('rdube88', password='pw', first_name='Rudo', last_name='Chuma')
        due_today = self.make_booking(delivery_date=today, status='confirmed', time_slot='evening')
        early_today = self.make_booking(delivery_date=today, status='pending', time_slot='morning')
        later = self.make_booking(delivery_date=today + timedelta(days=3), status='pending', city='Gweru',
                                  user=other, phone='0719999999')
        past = self.make_booking(delivery_date=today - timedelta(days=2), status='delivered')

        context = self.client.get(reverse('dashboard_deliveries')).context
        self.assertEqual(context['counts'],
                         {'all': 4, 'pending': 2, 'confirmed': 1, 'in_transit': 0, 'delivered': 1, 'cancelled': 0})
        self.assertEqual((context['active_status'], context['active_when'], context['today']), ('all', 'all', today))
        self.assertEqual(context['status_choices'], DeliveryBooking.STATUS_CHOICES)
        # The full list reads latest delivery date first.
        self.assertEqual(list(context['bookings']), [later, early_today, due_today, past])

        context = self.client.get(reverse('dashboard_deliveries'), {'when': 'today'}).context
        self.assertEqual(list(context['bookings']), [early_today, due_today])
        self.assertEqual(context['counts']['all'], 2)

        context = self.client.get(reverse('dashboard_deliveries'), {'when': 'upcoming', 'status': 'pending'}).context
        self.assertEqual(list(context['bookings']), [early_today, later])
        self.assertEqual((context['active_when'], context['active_status']), ('upcoming', 'pending'))

        for query in ('gweru', 'rdube88', 'RUDO', 'chuma', '0719999999'):
            context = self.client.get(reverse('dashboard_deliveries'), {'search': query}).context
            self.assertEqual(list(context['bookings']), [later], query)
        context = self.client.get(reverse('dashboard_deliveries'), {'search': 'moyo', 'when': 'x', 'status': 'y'}).context
        self.assertEqual(len(context['bookings']), 3)
        self.assertEqual((context['active_when'], context['active_status']), ('all', 'all'))


    def test_in_transit_is_spelt_one_way_on_the_page(self):
        # The tab is template text; the badge and the select use the model's label.
        self.make_booking(status='in_transit')

        response = self.client.get(reverse('dashboard_deliveries'))

        self.assertEqual(dict(DeliveryBooking.STATUS_CHOICES)['in_transit'], 'In transit')
        self.assertContains(response, 'In transit <span class="tab-count">1</span>')
        self.assertNotContains(response, 'In Transit')


@override_settings(**TEST_SETTINGS)
class RebookingTests(DashboardTestCase):
    def booking_form(self):
        return {
            'delivery_date': (timezone.localdate() + timedelta(days=2)).isoformat(), 'time_slot': 'afternoon',
            'delivery_address': '12 Samora Machel Ave', 'delivery_city': 'Harare', 'delivery_phone': '0771234567',
        }

    def test_customer_can_book_again_after_staff_cancel_the_delivery(self):
        order = self.make_order('pending')
        booking = self.make_booking(order, status='confirmed')
        self.client.force_login(self.staff)
        self.client.post(reverse('dashboard_delivery_status', args=[booking.id]), {'status': 'cancelled'})

        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('delivery_booking')).status_code, 200)
        response = self.client.post(reverse('delivery_booking'), self.booking_form())

        self.assertRedirects(response, reverse('delivery_bookings'))
        rebooked = DeliveryBooking.objects.exclude(pk=booking.pk).get()
        self.assertEqual((rebooked.order, rebooked.status), (order, 'pending'))

    def test_an_active_booking_still_blocks_a_second_one(self):
        order = self.make_order('pending')
        self.make_booking(order, status='cancelled')
        self.make_booking(order, status='confirmed')
        self.client.force_login(self.customer)

        response = self.client.get(reverse('delivery_booking'))

        self.assertRedirects(response, reverse('delivery_bookings'))

    def assert_customer_can_rebook(self, order, cancelled):
        self.client.force_login(self.customer)
        page = self.client.get(reverse('delivery_booking'))
        self.assertEqual(page.status_code, 200)
        # The page names the order the new booking will be linked to.
        self.assertEqual(page.context['user_orders'].first(), order)
        response = self.client.post(reverse('delivery_booking'), self.booking_form())

        self.assertRedirects(response, reverse('delivery_bookings'))
        rebooked = DeliveryBooking.objects.exclude(pk=cancelled.pk).get()
        self.assertEqual((rebooked.order, rebooked.status), (order, 'pending'))

    def test_rebooking_works_after_the_dashboard_has_shipped_the_order(self):
        order = self.make_order('pending')
        booking = self.make_booking(order, status='confirmed')
        self.client.force_login(self.staff)
        url = reverse('dashboard_delivery_status', args=[booking.id])
        # Going out for delivery ships the order; then the driver can't deliver.
        self.client.post(url, {'status': 'in_transit'})
        self.client.post(url, {'status': 'cancelled'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'shipped')

        self.assert_customer_can_rebook(order, booking)

    def test_rebooking_works_for_an_order_staff_are_packing(self):
        order = self.make_order('pending')
        booking = self.make_booking(order, status='confirmed')
        self.client.force_login(self.staff)
        self.client.post(reverse('dashboard_order_status', args=[order.id]), {'status': 'processing'})
        self.client.post(reverse('dashboard_delivery_status', args=[booking.id]), {'status': 'cancelled'})

        self.assert_customer_can_rebook(order, booking)

    def test_an_older_order_on_its_way_does_not_block_booking_a_newer_one(self):
        shipped = self.make_order('shipped', on=timezone.localdate() - timedelta(days=3))
        on_its_way = self.make_booking(shipped, status='in_transit')
        newer = self.make_order('pending')

        self.assert_customer_can_rebook(newer, on_its_way)

    def test_finished_orders_cannot_be_booked(self):
        self.make_order('delivered')
        self.make_order('cancelled')
        self.client.force_login(self.customer)

        response = self.client.get(reverse('delivery_booking'))
        self.assertRedirects(response, reverse('product_list'))

        response = self.client.post(reverse('delivery_booking'), self.booking_form())
        self.assertRedirects(response, reverse('product_list'))
        self.assertFalse(DeliveryBooking.objects.exists())


@override_settings(**TEST_SETTINGS)
class CustomerOrderPageTests(DashboardTestCase):
    """The order page offers a delivery booking exactly when the booking view would take one."""

    def page(self, order):
        self.client.force_login(self.customer)
        return self.client.get(reverse('order_detail', args=[order.id]))

    def test_a_delivery_cancelled_by_staff_can_be_booked_again_from_the_order_page(self):
        order = self.make_order('pending')
        booking = self.make_booking(order, status='confirmed')
        self.client.force_login(self.staff)
        url = reverse('dashboard_delivery_status', args=[booking.id])
        self.client.post(url, {'status': 'in_transit'})
        self.client.post(url, {'status': 'cancelled'})

        response = self.page(order)

        self.assertEqual(response.context['order'].status, 'shipped')
        self.assertEqual(response.context['delivery'], booking)
        self.assertTrue(response.context['can_book_delivery'])
        self.assertContains(response, 'Your delivery booking was cancelled')
        self.assertContains(response, f'href="{reverse("delivery_booking")}" class="btn btn-primary')
        # The cancelled booking's fee is no longer owed.
        self.assertContains(response, 'Booking cancelled')

    def test_an_order_never_booked_can_be_booked_while_it_is_open(self):
        for status, expected in [('pending', True), ('processing', True), ('shipped', True),
                                 ('delivered', False), ('cancelled', False)]:
            with self.subTest(status=status):
                response = self.page(self.make_order(status))
                self.assertIsNone(response.context['delivery'])
                self.assertEqual(response.context['can_book_delivery'], expected)

    def test_a_live_booking_is_shown_and_not_offered_again(self):
        order = self.make_order('processing')
        self.make_booking(order, status='cancelled', on=timezone.localdate() - timedelta(days=2))
        rebooked = self.make_booking(order, status='pending', on=timezone.localdate() - timedelta(days=1))
        # Even when a newer booking was cancelled since, the live one is the one that counts.
        self.make_booking(order, status='cancelled')

        response = self.page(order)

        self.assertEqual(response.context['delivery'], rebooked)
        self.assertFalse(response.context['can_book_delivery'])
        self.assertNotContains(response, f'href="{reverse("delivery_booking")}" class="btn btn-primary')

    def test_a_finished_order_with_a_cancelled_delivery_is_not_offered_a_booking(self):
        order = self.make_order('delivered')
        self.make_booking(order, status='cancelled')

        response = self.page(order)

        self.assertFalse(response.context['can_book_delivery'])
        self.assertNotContains(response, 'Your delivery booking was cancelled')

    def test_quantity_and_price_are_folded_under_the_name_for_phones(self):
        response = self.page(self.make_order('pending', [(self.rice, 3)]))

        # Below sm the Qty and Price columns are hidden; a fixed minimum width used to push Total off-screen.
        self.assertContains(response, '<p class="mt-0.5 text-xs text-slate-500 sm:hidden">3 × $8.00</p>')
        self.assertNotContains(response, 'min-w-[34rem]')


@override_settings(**TEST_SETTINGS)
class CustomerCancelTests(DashboardTestCase):
    """The customer's own cancel must not return stock a staff cancel already returned."""

    def test_cancelling_returns_the_stock_and_the_items_to_the_cart(self):
        order = self.make_order('pending', [(self.rice, 3)])
        self.client.force_login(self.customer)

        response = self.client.post(reverse('cancel_order', args=[order.id]))

        self.assertRedirects(response, reverse('cart'))
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 23)
        self.assertFalse(Order.objects.filter(pk=order.pk).exists())
        self.assertEqual(CartItem.objects.get(cart__user=self.customer).quantity, 3)

    def test_a_staff_cancel_that_lands_first_wins(self):
        order = self.make_order('pending', [(self.rice, 3)])
        self.client.force_login(self.customer)
        real = views.restore_order_to_cart

        def staff_cancel_first(user, stale_order):
            # The customer's view has already checked the status; staff cancel now.
            self.assertTrue(dashboard.cancel_order(Order.objects.get(pk=order.pk)))
            return real(user, stale_order)

        with mock.patch.object(views, 'restore_order_to_cart', staff_cancel_first):
            response = self.client.post(reverse('cancel_order', args=[order.id]))

        self.assertRedirects(response, reverse('order_history'))
        self.assertEqual(self.flashes(response)[-1], ('error', 'This order can no longer be cancelled.'))
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 23)
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'cancelled')
        self.assertFalse(CartItem.objects.exists())

    def test_a_double_submit_returns_the_stock_once(self):
        order = self.make_order('pending', [(self.rice, 3)])
        stale = Order.objects.get(pk=order.pk)

        self.assertTrue(views.restore_order_to_cart(self.customer, order))
        self.assertFalse(views.restore_order_to_cart(self.customer, stale))

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 23)


@override_settings(**TEST_SETTINGS)
class HiddenProductCheckoutTests(DashboardTestCase):
    """Hiding is how staff withdraw a product, so it has to hold for carts filled earlier."""

    ADDRESS = {'delivery_address': '12 Samora Machel Ave', 'delivery_city': 'Harare', 'delivery_phone': '0771234567'}

    def setUp(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('add_to_cart', args=[self.rice.id]), {'quantity': 2})
        self.staff_client = Client()
        self.staff_client.force_login(self.staff)

    def toggle(self):
        return self.staff_client.post(reverse('dashboard_toggle_available', args=[self.rice.id])).json()

    def test_a_product_hidden_after_it_was_carted_cannot_be_checked_out(self):
        self.assertFalse(self.toggle()['is_available'])

        response = self.client.post(reverse('checkout'), self.ADDRESS)

        self.assertRedirects(response, reverse('cart'))
        level, message = self.flashes(response)[-1]
        self.assertEqual(level, 'error')
        self.assertIn('"Rice 5kg" is no longer available', message)
        self.assertFalse(Order.objects.exists())
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 20)
        # The item stays in the cart for the customer to remove.
        self.assertEqual(CartItem.objects.get(cart__user=self.customer).quantity, 2)

    def test_the_cart_marks_the_hidden_item_and_holds_checkout_until_it_is_removed(self):
        item = CartItem.objects.get(cart__user=self.customer)
        stepper = f'action="{reverse("update_cart_item", args=[item.id])}"'
        checkout = f'href="{reverse("checkout")}"'

        response = self.client.get(reverse('cart'))
        self.assertEqual(response.context['unavailable_count'], 0)
        self.assertContains(response, stepper)
        self.assertContains(response, checkout)
        self.assertNotContains(response, 'No longer available')

        self.toggle()
        response = self.client.get(reverse('cart'))

        self.assertEqual(response.context['unavailable_count'], 1)
        self.assertContains(response, 'No longer available</span>')
        self.assertNotContains(response, stepper)
        self.assertNotContains(response, checkout)
        # Removing it is the way out, so that button stays.
        self.assertContains(response, f'action="{reverse("remove_from_cart", args=[item.id])}"')

    def test_the_same_cart_checks_out_once_the_product_is_shown_again(self):
        self.toggle()
        self.assertTrue(self.toggle()['is_available'])

        response = self.client.post(reverse('checkout'), self.ADDRESS)

        order = Order.objects.get()
        self.assertRedirects(response, reverse('order_detail', args=[order.id]))
        self.rice.refresh_from_db()
        self.assertEqual(self.rice.stock_quantity, 18)

    def test_running_out_of_stock_still_gets_the_stock_message(self):
        Product.objects.filter(pk=self.rice.pk).update(stock_quantity=1)

        response = self.client.post(reverse('checkout'), self.ADDRESS)

        self.assertRedirects(response, reverse('cart'))
        self.assertIn('no longer has enough stock', self.flashes(response)[-1][1])
        self.assertFalse(Order.objects.exists())


@override_settings(**TEST_SETTINGS)
class HeaderSearchTests(DashboardTestCase):
    """The header's product search (desktop and mobile copies) only echoes the shop's own ?search=."""

    HEADER_BOX = '<input type="search" name="search" value="{}" placeholder="Search products…"'

    def test_dashboard_searches_stay_out_of_the_header_box(self):
        self.client.force_login(self.staff)
        pages = [('dashboard_orders', '0771234567'), ('dashboard_deliveries', 'Samora'), ('dashboard_inventory', 'rice')]
        for name, term in pages:
            with self.subTest(page=name):
                response = self.client.get(reverse(name), {'search': term})
                self.assertContains(response, self.HEADER_BOX.format(''), count=2)
                # Only the page's own search box holds the term.
                self.assertContains(response, f'value="{term}"', count=1)

    def test_the_shop_still_shows_its_search_term_in_the_header(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse('product_list'), {'search': 'rice'})

        self.assertContains(response, self.HEADER_BOX.format('rice'), count=2)


@override_settings(**TEST_SETTINGS)
class MessagesPageTests(DashboardTestCase):
    def test_filters_and_counts(self):
        ContactMessage.objects.create(name='Rudo', subject='Late', message='Late.', message_type='complaint',
                                      is_urgent=True)
        ContactMessage.objects.create(name='Tendai', subject='Hours', message='Hours?', is_read=True, status='replied')
        self.client.force_login(self.staff)

        response = self.client.get(reverse('dashboard_messages'))
        context = response.context
        self.assertTemplateUsed(response, 'supermarket/dashboard/messages.html')
        self.assertEqual(
            (context['total_messages'], context['unread_messages'], context['total_complaints'],
             context['urgent_count'], context['open_count'], context['active_filter']),
            (2, 1, 1, 1, 1, 'all'),
        )
        self.assertEqual(context['nav']['active'], 'messages')
        self.assertEqual(context['nav']['open_messages'], 1)
        self.assertContains(response, 'href="?filter=open"')
        self.assertNotContains(response, '#messages')

        for name in ('urgent', 'complaints', 'unread', 'open'):
            context = self.client.get(reverse('dashboard_messages'), {'filter': name}).context
            self.assertEqual([message.name for message in context['contact_messages']], ['Rudo'], name)
            self.assertEqual(context['active_filter'], name)

    def test_message_detail_links_back_to_the_messages_page(self):
        message = ContactMessage.objects.create(name='Rudo', subject='Late', message='Late.')
        self.client.force_login(self.staff)

        response = self.client.get(reverse('message_detail', args=[message.id]))

        self.assertContains(response, f'href="{reverse("dashboard_messages")}"')
        self.assertContains(response, 'Back to messages')
