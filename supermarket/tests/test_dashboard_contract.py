"""Contract tests for the staff dashboard.

Written from the build contract alone and driven through the URLs, without
reading the implementation, so that a rule the implementation and its own
tests both got wrong still fails here. The focus is on the rules where a
mistake costs the owner money: what counts as revenue and when, and what
happens to stock.
"""
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from itertools import count
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.contrib.messages import constants as flash_levels, get_messages
from django.db.models import F
from django.db.models.signals import pre_save
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from supermarket.models import (Category, ContactMessage, DeliveryBooking, Order, OrderItem,
                                Product, StockEntry)

# Production-only settings get in the way of the test client: the HTTPS
# redirect turns every request into a 301, and the manifest static storage
# needs collectstatic to have run.
TEST_SETTINGS = {
    'SECURE_SSL_REDIRECT': False,
    'STORAGES': {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
    'PASSWORD_HASHERS': ['django.contrib.auth.hashers.MD5PasswordHasher'],
}

HARARE = ZoneInfo('Africa/Harare')

# A Thursday, deliberately not the day the tests run: a dashboard that asks
# the operating system for the date instead of Django fails straight away.
TODAY = date(2026, 3, 12)

_order_numbers = count(1)


def local_dt(day, hour=12, minute=0):
    """A shop-local moment, expressed in UTC the way the database stores it."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=HARARE).astimezone(dt_timezone.utc)


def freeze(moment):
    return mock.patch('django.utils.timezone.now', return_value=moment)


def monday_of(day):
    return day - timedelta(days=day.weekday())


def month_starts(first, how_many):
    year, month = first.year, first.month
    starts = []
    for _ in range(how_many):
        starts.append(date(year, month, 1))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return starts


@override_settings(**TEST_SETTINGS)
class DashboardContractCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('owner', password='pw', is_staff=True, first_name='Ronald')
        cls.customer = User.objects.create_user('tendai', password='pw', first_name='Tendai', last_name='Moyo')
        cls.category = Category.objects.create(name='Groceries')

    def make_product(self, name='Mealie meal 10kg', price='8.00', stock=20, **extra):
        return Product.objects.create(
            name=name, description='Test product', category=extra.pop('category', self.category),
            price=Decimal(price), stock_quantity=stock, **extra,
        )

    def make_order(self, total='10.00', status='pending', at=None, items=(), user=None):
        order = Order.objects.create(
            user=user or self.customer, order_number=f'CT{next(_order_numbers):08d}', status=status,
            total_amount=Decimal(total), delivery_address='12 Samora Machel Ave',
            delivery_city='Harare', delivery_phone='0771234567',
        )
        for product, quantity, price in items:
            OrderItem.objects.create(order=order, product=product, quantity=quantity, price=Decimal(price))
        if at is not None:
            Order.objects.filter(pk=order.pk).update(created_at=at)
        return order

    def make_booking(self, fee='5.00', status='pending', at=None, order=None, user=None,
                     delivery_date=None, time_slot='morning', **extra):
        booking = DeliveryBooking.objects.create(
            user=user or self.customer, order=order, status=status, delivery_fee=Decimal(fee),
            delivery_date=delivery_date or TODAY, time_slot=time_slot,
            delivery_address=extra.pop('delivery_address', '12 Samora Machel Ave'),
            delivery_city='Harare', delivery_phone='0771234567', **extra,
        )
        if at is not None:
            DeliveryBooking.objects.filter(pk=booking.pk).update(created_at=at)
        return booking

    def make_entry(self, product, quantity, unit_cost=None, kind='restock', at=None):
        entry = StockEntry.objects.create(
            product=product, kind=kind, quantity=quantity,
            unit_cost=None if unit_cost is None else Decimal(unit_cost),
        )
        if at is not None:
            StockEntry.objects.filter(pk=entry.pk).update(created_at=at)
        return entry

    def staff_get(self, url_name, args=(), /, **params):
        self.client.force_login(self.staff)
        response = self.client.get(reverse(url_name, args=args), params)
        self.assertEqual(response.status_code, 200)
        return response

    def staff_post(self, url_name, args=(), /, **data):
        self.client.force_login(self.staff)
        # Nothing here renders a page between POSTs, so earlier toasts would
        # still be queued and blur which request said what.
        self.client.cookies.pop('messages', None)
        session = self.client.session
        if session.pop('_messages', None) is not None:
            session.save()
        return self.client.post(reverse(url_name, args=args), data)

    def overview(self, range_key=None):
        params = {'range': range_key} if range_key else {}
        return self.staff_get('founder_dashboard', **params).context

    def flashes(self, response):
        return list(get_messages(response.wsgi_request))

    def assertFlashLevel(self, response, level):
        levels = [message.level for message in self.flashes(response)]
        self.assertEqual(levels, [level], [str(m) for m in self.flashes(response)])

    def assertMoney(self, value, expected):
        self.assertIsInstance(value, Decimal)
        self.assertEqual(value, Decimal(expected))
        self.assertEqual(value.as_tuple().exponent, -2, f'{value!r} is not quantized to 0.01')

    def stock_of(self, product):
        return Product.objects.get(pk=product.pk).stock_quantity


class FrozenClockCase(DashboardContractCase):
    """Late in the evening of TODAY, shop time."""

    def setUp(self):
        patcher = freeze(local_dt(TODAY, 23, 45))
        patcher.start()
        self.addCleanup(patcher.stop)


# ---------------------------------------------------------------------------
# Who may use the dashboard
# ---------------------------------------------------------------------------

class AccessTests(DashboardContractCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.product = Product.objects.create(
            name='Cooking oil 2L', description='x', category=cls.category, price=Decimal('4.00'), stock_quantity=9,
        )
        cls.order = Order.objects.create(
            user=cls.customer, order_number='ACCESS0001', total_amount=Decimal('8.00'),
            delivery_address='1 First St', delivery_city='Harare', delivery_phone='0771234567',
        )
        OrderItem.objects.create(order=cls.order, product=cls.product, quantity=2, price=Decimal('4.00'))
        cls.booking = DeliveryBooking.objects.create(
            user=cls.customer, order=cls.order, delivery_date=TODAY, time_slot='morning',
            delivery_address='1 First St', delivery_city='Harare', delivery_phone='0771234567',
            delivery_fee=Decimal('5.00'),
        )
        pid, oid, bid = cls.product.id, cls.order.id, cls.booking.id
        # (url name, args, path, template) straight from the contract table.
        cls.pages = [
            ('founder_dashboard', [], '/founder/', 'overview.html'),
            ('dashboard_inventory', [], '/founder/inventory/', 'inventory.html'),
            ('dashboard_product_add', [], '/founder/inventory/add/', 'product_form.html'),
            ('dashboard_product_edit', [pid], f'/founder/inventory/{pid}/edit/', 'product_form.html'),
            ('dashboard_stock_history', [], '/founder/inventory/history/', 'stock_history.html'),
            ('dashboard_orders', [], '/founder/orders/', 'orders.html'),
            ('dashboard_order_detail', [oid], f'/founder/orders/{oid}/', 'order_detail.html'),
            ('dashboard_deliveries', [], '/founder/deliveries/', 'deliveries.html'),
            ('dashboard_messages', [], '/founder/messages/', 'messages.html'),
        ]
        cls.post_only = [
            ('dashboard_restock', [pid], f'/founder/inventory/{pid}/restock/', {'quantity': '7'}),
            ('dashboard_adjust_stock', [pid], f'/founder/inventory/{pid}/adjust/', {'new_quantity': '1'}),
            ('dashboard_toggle_available', [pid], f'/founder/inventory/{pid}/toggle/', {}),
            ('dashboard_order_status', [oid], f'/founder/orders/{oid}/status/', {'status': 'cancelled'}),
            ('dashboard_delivery_status', [bid], f'/founder/deliveries/{bid}/status/', {'status': 'delivered'}),
        ]

    def assertNothingChanged(self):
        product = Product.objects.get(pk=self.product.pk)
        self.assertEqual(product.stock_quantity, 9)
        self.assertTrue(product.is_available)
        self.assertEqual(Order.objects.get(pk=self.order.pk).status, 'pending')
        self.assertEqual(DeliveryBooking.objects.get(pk=self.booking.pk).status, 'pending')
        self.assertFalse(StockEntry.objects.exists())

    def test_url_names_resolve_to_the_contract_paths(self):
        for name, args, path, _ in self.pages + self.post_only:
            with self.subTest(name=name):
                self.assertEqual(reverse(name, args=args), path)

    def test_anonymous_visitors_are_sent_to_the_login_page(self):
        for name, args, path, _ in self.pages:
            with self.subTest(name=name):
                response = self.client.get(path)
                self.assertRedirects(response, f'/login/?next={path}', fetch_redirect_response=False)

    def test_customers_are_turned_away_from_every_page(self):
        self.client.force_login(self.customer)
        for name, args, path, _ in self.pages:
            with self.subTest(name=name):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/login/'), response['Location'])

    def test_staff_see_every_page_with_its_contract_template_and_nav(self):
        self.client.force_login(self.staff)
        for name, args, path, template in self.pages:
            with self.subTest(name=name):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f'supermarket/dashboard/{template}')
                self.assertTemplateUsed(response, 'partials/dashboard_nav.html')
                self.assertEqual(
                    set(response.context['nav']),
                    {'active', 'out_of_stock', 'low_stock', 'pending_orders', 'pending_deliveries', 'open_messages'},
                )

    def test_anonymous_posts_change_nothing(self):
        for name, args, path, data in self.post_only:
            with self.subTest(name=name):
                response = self.client.post(path, data)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/login/'), response['Location'])
        self.assertNothingChanged()

    def test_customer_posts_change_nothing(self):
        self.client.force_login(self.customer)
        for name, args, path, data in self.post_only:
            with self.subTest(name=name):
                response = self.client.post(path, data)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response['Location'].startswith('/login/'), response['Location'])
        self.assertNothingChanged()

    def test_customer_cannot_add_or_edit_products(self):
        self.client.force_login(self.customer)
        form = {'name': 'Free stuff', 'description': 'x', 'category': self.category.id, 'price': '0.01',
                'is_available': 'on', 'opening_stock': '50'}
        self.client.post(reverse('dashboard_product_add'), form)
        self.client.post(reverse('dashboard_product_edit', args=[self.product.id]), form)

        self.assertFalse(Product.objects.filter(name='Free stuff').exists())
        self.assertEqual(Product.objects.get(pk=self.product.pk).price, Decimal('4.00'))
        self.assertNothingChanged()

    def test_get_to_a_post_only_url_is_405_and_changes_nothing(self):
        self.client.force_login(self.staff)
        for name, args, path, data in self.post_only:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(path, data).status_code, 405)
        self.assertNothingChanged()

    def test_get_to_a_post_only_url_never_works_for_outsiders(self):
        for user in (None, self.customer):
            if user:
                self.client.force_login(user)
            for name, args, path, data in self.post_only:
                with self.subTest(name=name, user=user):
                    self.assertIn(self.client.get(path, data).status_code, (302, 405))
        self.assertNothingChanged()

    def test_unknown_ids_are_404(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('dashboard_order_detail', args=[99999])).status_code, 404)
        self.assertEqual(self.client.get(reverse('dashboard_product_edit', args=[99999])).status_code, 404)
        self.assertEqual(self.client.post(reverse('dashboard_restock', args=[99999]), {'quantity': 1}).status_code, 404)
        self.assertEqual(
            self.client.post(reverse('dashboard_order_status', args=[99999]), {'status': 'shipped'}).status_code, 404)
        self.assertEqual(
            self.client.post(reverse('dashboard_delivery_status', args=[99999]), {'status': 'confirmed'}).status_code, 404)


class NextRedirectTests(DashboardContractCase):
    OFF_SITE = [
        'https://evil.example.com/founder/',
        '//evil.example.com/founder/',
        'http:evil.example.com',
        '/\\evil.example.com',
        'javascript:alert(1)',
    ]

    def setUp(self):
        self.product = self.make_product(stock=10)
        self.order = self.make_order()
        self.booking = self.make_booking(order=self.order)

    def cases(self):
        """(url name, args, a valid POST, the list page it falls back to)."""
        return [
            ('dashboard_restock', [self.product.id], {'quantity': '1'}, reverse('dashboard_inventory')),
            ('dashboard_adjust_stock', [self.product.id], {'new_quantity': '4'}, reverse('dashboard_inventory')),
            ('dashboard_order_status', [self.order.id], {'status': 'processing'}, reverse('dashboard_orders')),
            ('dashboard_delivery_status', [self.booking.id], {'status': 'confirmed'}, reverse('dashboard_deliveries')),
        ]

    def test_off_site_next_is_ignored(self):
        for name, args, data, fallback in self.cases():
            for target in self.OFF_SITE:
                with self.subTest(name=name, next=target):
                    response = self.staff_post(name, args, next=target, **data)
                    self.assertRedirects(response, fallback, fetch_redirect_response=False)

    def test_off_site_next_is_ignored_when_the_post_is_invalid_too(self):
        bad = {'dashboard_restock': {'quantity': '0'}, 'dashboard_adjust_stock': {'new_quantity': '-1'},
               'dashboard_order_status': {'status': 'nope'}, 'dashboard_delivery_status': {'status': 'nope'}}
        for name, args, _, fallback in self.cases():
            with self.subTest(name=name):
                response = self.staff_post(name, args, next='https://evil.example.com/', **bad[name])
                self.assertRedirects(response, fallback, fetch_redirect_response=False)

    def test_missing_next_falls_back_to_the_list_page(self):
        for name, args, data, fallback in self.cases():
            with self.subTest(name=name):
                self.assertRedirects(self.staff_post(name, args, **data), fallback, fetch_redirect_response=False)

    def test_same_site_next_is_followed_with_its_query_string(self):
        for name, args, data, fallback in self.cases():
            target = f'{fallback}?page=2&search=oil'
            with self.subTest(name=name):
                response = self.staff_post(name, args, next=target, **data)
                self.assertRedirects(response, target, fetch_redirect_response=False)


# ---------------------------------------------------------------------------
# Revenue: what counts
# ---------------------------------------------------------------------------

class RevenueRulesTests(FrozenClockCase):
    def test_default_and_unknown_ranges_are_30_days(self):
        for params in ({}, {'range': 'forever'}, {'range': ''}, {'range': '30D '}):
            with self.subTest(params=params):
                context = self.staff_get('founder_dashboard', **params).context
                self.assertEqual(context['range_key'], '30d')
                self.assertEqual(context['period_end'], TODAY)
                self.assertEqual(context['period_start'], TODAY - timedelta(days=29))
        self.assertEqual(context['range_label'], 'Last 30 days')
        self.assertEqual(context['previous_label'], 'previous 30 days')
        self.assertEqual(
            list(context['range_options']),
            [('7d', '7 days'), ('30d', '30 days'), ('90d', '90 days'), ('12m', '12 months')],
        )

    def test_every_kpi_key_is_present(self):
        self.assertEqual(set(self.overview()['kpis']), {
            'total_revenue', 'prev_total_revenue', 'revenue_change_pct',
            'goods_revenue', 'goods_revenue_delivered', 'delivery_revenue', 'delivery_revenue_delivered',
            'orders_count', 'units_sold', 'average_order_value', 'deliveries_booked',
            'stock_bought_units', 'stock_bought_cost',
        })

    def test_an_empty_shop_reports_zero_money_not_none(self):
        kpis = self.overview()['kpis']
        for key in ('total_revenue', 'prev_total_revenue', 'goods_revenue', 'goods_revenue_delivered',
                    'delivery_revenue', 'delivery_revenue_delivered', 'average_order_value', 'stock_bought_cost'):
            with self.subTest(key=key):
                self.assertMoney(kpis[key], '0.00')
        for key in ('orders_count', 'units_sold', 'deliveries_booked', 'stock_bought_units'):
            with self.subTest(key=key):
                self.assertEqual(kpis[key], 0)
        self.assertIsNone(kpis['revenue_change_pct'])

    def test_goods_sales_count_every_status_except_cancelled(self):
        self.make_order('1.00', status='pending')
        self.make_order('2.00', status='processing')
        self.make_order('4.00', status='shipped')
        self.make_order('8.00', status='delivered')
        self.make_order('16.00', status='cancelled')

        kpis = self.overview()['kpis']
        self.assertMoney(kpis['goods_revenue'], '15.00')
        self.assertMoney(kpis['goods_revenue_delivered'], '8.00')
        self.assertMoney(kpis['total_revenue'], '15.00')
        self.assertEqual(kpis['orders_count'], 4)

    def test_delivery_fees_count_every_status_except_cancelled(self):
        self.make_booking('1.00', status='pending')
        self.make_booking('2.00', status='confirmed')
        self.make_booking('4.00', status='in_transit')
        self.make_booking('8.00', status='delivered')
        self.make_booking('16.00', status='cancelled')

        kpis = self.overview()['kpis']
        self.assertMoney(kpis['delivery_revenue'], '15.00')
        self.assertMoney(kpis['delivery_revenue_delivered'], '8.00')
        self.assertMoney(kpis['goods_revenue'], '0.00')
        self.assertMoney(kpis['total_revenue'], '15.00')

    def test_total_is_goods_plus_delivery_and_delivered_figures_stay_separate(self):
        delivered = self.make_order('40.25', status='delivered')
        waiting = self.make_order('19.75', status='pending')
        # The booking's status decides the delivered fee figure, not its order's.
        self.make_booking('5.00', status='pending', order=delivered)
        self.make_booking('10.50', status='delivered', order=waiting)

        kpis = self.overview()['kpis']
        self.assertMoney(kpis['goods_revenue'], '60.00')
        self.assertMoney(kpis['goods_revenue_delivered'], '40.25')
        self.assertMoney(kpis['delivery_revenue'], '15.50')
        self.assertMoney(kpis['delivery_revenue_delivered'], '10.50')
        self.assertMoney(kpis['total_revenue'], '75.50')

    def test_an_order_with_several_items_and_a_booking_is_counted_once(self):
        maize, oil = self.make_product('Maize'), self.make_product('Oil')
        order = self.make_order('30.00', items=[(maize, 1, '10.00'), (oil, 2, '5.00'), (maize, 1, '10.00')])
        self.make_booking('5.00', order=order)
        self.make_booking('5.00', order=order, status='cancelled')

        kpis = self.overview()['kpis']
        self.assertMoney(kpis['goods_revenue'], '30.00')
        self.assertMoney(kpis['delivery_revenue'], '5.00')
        self.assertEqual(kpis['orders_count'], 1)
        self.assertEqual(kpis['units_sold'], 4)

    def test_units_sold_ignore_cancelled_orders_and_orders_outside_the_period(self):
        maize = self.make_product('Maize')
        self.make_order('20.00', items=[(maize, 2, '10.00')])
        self.make_order('30.00', status='delivered', items=[(maize, 3, '10.00')])
        self.make_order('70.00', status='cancelled', items=[(maize, 7, '10.00')])
        self.make_order('110.00', items=[(maize, 11, '10.00')], at=local_dt(TODAY - timedelta(days=30), 12))

        self.assertEqual(self.overview('30d')['kpis']['units_sold'], 5)

    def test_average_order_value(self):
        self.make_order('5.00')
        self.make_order('2.50', status='delivered')
        self.make_order('2.50', status='shipped')
        # A cancelled order brings no money, so it must not drag the average down.
        self.make_order('500.00', status='cancelled')

        self.assertMoney(self.overview()['kpis']['average_order_value'], '3.33')

    def test_average_order_value_is_zero_without_orders(self):
        self.make_order('500.00', status='cancelled')
        self.make_booking('5.00')

        kpis = self.overview()['kpis']
        self.assertEqual(kpis['orders_count'], 0)
        self.assertMoney(kpis['average_order_value'], '0.00')

    def test_deliveries_booked_counts_bookings_made_in_the_period(self):
        self.make_booking('5.00')
        self.make_booking('5.00', status='delivered')
        self.make_booking('5.00', at=local_dt(TODAY - timedelta(days=7), 23, 30))

        self.assertEqual(self.overview('7d')['kpis']['deliveries_booked'], 2)


class StockBoughtTests(FrozenClockCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product()

    def test_cost_ignores_entries_without_a_cost_but_units_count_them(self):
        self.make_entry(self.product, 10, '1.25')
        self.make_entry(self.product, 3, '0.99')
        self.make_entry(self.product, 40)

        kpis = self.overview()['kpis']
        self.assertEqual(kpis['stock_bought_units'], 53)
        self.assertMoney(kpis['stock_bought_cost'], '15.47')

    def test_a_free_restock_costs_nothing_rather_than_being_skipped(self):
        self.make_entry(self.product, 6, '0.00')
        self.make_entry(self.product, 2, '3.00')

        kpis = self.overview()['kpis']
        self.assertEqual(kpis['stock_bought_units'], 8)
        self.assertMoney(kpis['stock_bought_cost'], '6.00')

    def test_corrections_are_not_stock_bought(self):
        self.make_entry(self.product, 5, '2.00')
        self.make_entry(self.product, 9, '2.00', kind='adjustment')
        self.make_entry(self.product, -4, kind='adjustment')

        kpis = self.overview()['kpis']
        self.assertEqual(kpis['stock_bought_units'], 5)
        self.assertMoney(kpis['stock_bought_cost'], '10.00')

    def test_only_entries_inside_the_period_count(self):
        start = TODAY - timedelta(days=6)
        self.make_entry(self.product, 1, '1.00', at=local_dt(TODAY, 23, 30))
        self.make_entry(self.product, 2, '1.00', at=local_dt(start, 0, 30))
        self.make_entry(self.product, 4, '1.00', at=local_dt(start - timedelta(days=1), 23, 30))

        kpis = self.overview('7d')['kpis']
        self.assertEqual(kpis['stock_bought_units'], 3)
        self.assertMoney(kpis['stock_bought_cost'], '3.00')

    def test_restocking_through_the_dashboard_shows_up_as_stock_bought(self):
        self.staff_post('dashboard_restock', [self.product.id], quantity='12', unit_cost='2.50')
        self.staff_post('dashboard_restock', [self.product.id], quantity='8')
        self.staff_post('dashboard_adjust_stock', [self.product.id], new_quantity='100')

        kpis = self.overview()['kpis']
        self.assertEqual(kpis['stock_bought_units'], 20)
        self.assertMoney(kpis['stock_bought_cost'], '30.00')


# ---------------------------------------------------------------------------
# Revenue: when it counts
# ---------------------------------------------------------------------------

class PeriodWindowTests(FrozenClockCase):
    def window(self, range_key, today=TODAY):
        """(start, previous start) of a range, worked out independently of the app."""
        if range_key == '12m':
            start = month_starts(today.replace(day=1), 1)[0]
            for _ in range(11):
                start = (start - timedelta(days=1)).replace(day=1)
            return start, start.replace(year=start.year - 1)
        days = int(range_key[:-1])
        start = today - timedelta(days=days - 1)
        return start, start - timedelta(days=days)

    def seed_edges(self, make, start, previous_start):
        """Rows worth powers of two around every edge, so a wrong sum names the culprit."""
        make('1', local_dt(TODAY, 23, 30))                                   # last evening of the period
        make('2', local_dt(start, 0, 30))                                    # just after the period opens
        make('4', local_dt(start - timedelta(days=1), 23, 30))               # just before: previous period
        make('8', local_dt(previous_start, 0, 30))                           # just after the previous opens
        make('16', local_dt(previous_start - timedelta(days=1), 23, 30))     # before both
        make('32', local_dt(TODAY + timedelta(days=1), 0, 30))               # after the period closes

    def test_hand_checked_period_dates(self):
        expected = {
            '7d': (date(2026, 3, 6), date(2026, 2, 27)),
            '30d': (date(2026, 2, 11), date(2026, 1, 12)),
            '90d': (date(2025, 12, 13), date(2025, 9, 14)),
            '12m': (date(2025, 4, 1), date(2024, 4, 1)),
        }
        for range_key, dates in expected.items():
            with self.subTest(range=range_key):
                self.assertEqual(self.window(range_key), dates)
                context = self.overview(range_key)
                self.assertEqual(context['period_start'], dates[0])
                self.assertEqual(context['period_end'], TODAY)

    def test_goods_sales_respect_the_local_day_edges(self):
        for range_key in ('7d', '30d', '90d', '12m'):
            with self.subTest(range=range_key):
                Order.objects.all().delete()
                self.seed_edges(lambda amount, at: self.make_order(f'{amount}.00', at=at), *self.window(range_key))

                kpis = self.overview(range_key)['kpis']
                self.assertMoney(kpis['goods_revenue'], '3.00')
                self.assertMoney(kpis['total_revenue'], '3.00')
                self.assertMoney(kpis['prev_total_revenue'], '12.00')
                self.assertEqual(kpis['orders_count'], 2)

    def test_delivery_fees_respect_the_local_day_edges(self):
        for range_key in ('7d', '30d', '90d', '12m'):
            with self.subTest(range=range_key):
                DeliveryBooking.objects.all().delete()
                self.seed_edges(lambda amount, at: self.make_booking(f'{amount}.00', at=at), *self.window(range_key))

                kpis = self.overview(range_key)['kpis']
                self.assertMoney(kpis['delivery_revenue'], '3.00')
                self.assertMoney(kpis['total_revenue'], '3.00')
                self.assertMoney(kpis['prev_total_revenue'], '12.00')
                self.assertEqual(kpis['deliveries_booked'], 2)

    def test_stock_bought_respects_the_local_day_edges(self):
        product = self.make_product()
        for range_key in ('7d', '30d', '90d', '12m'):
            with self.subTest(range=range_key):
                StockEntry.objects.all().delete()
                self.seed_edges(lambda amount, at: self.make_entry(product, int(amount), '1.00', at=at),
                                *self.window(range_key))

                kpis = self.overview(range_key)['kpis']
                self.assertEqual(kpis['stock_bought_units'], 3)
                self.assertMoney(kpis['stock_bought_cost'], '3.00')

    def test_the_window_is_closed_at_its_start_and_open_at_its_end(self):
        start, _ = self.window('7d')
        midnight = lambda day: local_dt(day, 0, 0)  # noqa: E731
        self.make_order('1.00', at=midnight(start))
        self.make_order('2.00', at=midnight(start) - timedelta(seconds=1))
        self.make_order('4.00', at=midnight(TODAY + timedelta(days=1)) - timedelta(seconds=1))
        self.make_order('8.00', at=midnight(TODAY + timedelta(days=1)))

        context = self.overview('7d')
        self.assertMoney(context['kpis']['goods_revenue'], '5.00')
        self.assertMoney(context['kpis']['prev_total_revenue'], '2.00')
        points = context['chart']['points']
        self.assertEqual((points[0]['goods'], points[-1]['goods']), (1.0, 4.0))

    def test_delivered_sub_totals_respect_the_window_too(self):
        start, previous_start = self.window('7d')
        self.make_order('1.00', status='delivered', at=local_dt(start, 0, 30))
        self.make_order('2.00', status='delivered', at=local_dt(start - timedelta(days=1), 23, 30))
        self.make_booking('4.00', status='delivered', at=local_dt(TODAY, 23, 30))
        self.make_booking('8.00', status='delivered', at=local_dt(start - timedelta(days=1), 23, 30))

        kpis = self.overview('7d')['kpis']
        self.assertMoney(kpis['goods_revenue_delivered'], '1.00')
        self.assertMoney(kpis['delivery_revenue_delivered'], '4.00')

    def test_just_after_local_midnight_today_is_the_local_date_not_the_utc_one(self):
        # 00:30 in Harare is still yesterday in UTC.
        with freeze(local_dt(TODAY, 0, 30)):
            self.make_order('9.00')
            self.make_order('2.00', at=local_dt(TODAY - timedelta(days=6), 0, 10))
            self.make_order('4.00', at=local_dt(TODAY - timedelta(days=7), 23, 50))
            context = self.overview('7d')

        self.assertEqual(context['period_end'], TODAY)
        self.assertEqual(context['period_start'], TODAY - timedelta(days=6))
        self.assertMoney(context['kpis']['goods_revenue'], '11.00')
        self.assertMoney(context['kpis']['prev_total_revenue'], '4.00')
        points = context['chart']['points']
        self.assertEqual(points[-1]['start'], TODAY.isoformat())
        self.assertEqual(points[-1]['goods'], 9.0)
        self.assertEqual(points[0]['goods'], 2.0)

    def test_twelve_months_start_on_the_first_of_the_month_eleven_months_ago(self):
        cases = [
            # A 31st: "same day eleven months ago" does not exist in April.
            (date(2026, 3, 31), date(2025, 4, 1), date(2024, 4, 1)),
            (date(2026, 1, 15), date(2025, 2, 1), date(2024, 2, 1)),
            (date(2026, 12, 5), date(2026, 1, 1), date(2025, 1, 1)),
            (date(2024, 2, 29), date(2023, 3, 1), date(2022, 3, 1)),
        ]
        for today, start, previous_start in cases:
            with self.subTest(today=today), freeze(local_dt(today, 12)):
                Order.objects.all().delete()
                self.make_order('1.00', at=local_dt(today, 11))
                self.make_order('2.00', at=local_dt(start, 0, 30))
                self.make_order('4.00', at=local_dt(start - timedelta(days=1), 23, 30))
                self.make_order('8.00', at=local_dt(previous_start, 0, 30))
                self.make_order('16.00', at=local_dt(previous_start - timedelta(days=1), 23, 30))
                context = self.overview('12m')

                self.assertEqual(context['period_start'], start)
                self.assertEqual(context['period_end'], today)
                self.assertMoney(context['kpis']['goods_revenue'], '3.00')
                self.assertMoney(context['kpis']['prev_total_revenue'], '12.00')
                points = context['chart']['points']
                self.assertEqual([p['start'] for p in points], [d.isoformat() for d in month_starts(start, 12)])
                self.assertEqual(points[0]['goods'], 2.0)
                self.assertEqual(points[-1]['goods'], 1.0)


class PreviousPeriodChangeTests(FrozenClockCase):
    PREVIOUS = local_dt(TODAY - timedelta(days=9), 12)

    def change(self):
        kpis = self.overview('7d')['kpis']
        return kpis['revenue_change_pct'], kpis

    def test_growth(self):
        self.make_order('100.00', at=self.PREVIOUS)
        self.make_order('150.00')
        pct, kpis = self.change()
        self.assertIsInstance(pct, Decimal)
        self.assertEqual(pct, Decimal('50.0'))
        self.assertEqual(pct.as_tuple().exponent, -1)
        self.assertMoney(kpis['prev_total_revenue'], '100.00')

    def test_one_decimal_place(self):
        self.make_order('30.00', at=self.PREVIOUS)
        self.make_order('40.00')
        pct, _ = self.change()
        self.assertEqual(pct, Decimal('33.3'))
        self.assertEqual(pct.as_tuple().exponent, -1)

    def test_a_fall_compares_total_revenue_including_delivery_fees(self):
        self.make_order('80.00', at=self.PREVIOUS)
        self.make_booking('20.00', at=self.PREVIOUS)
        self.make_order('50.00')
        self.make_booking('25.00')
        pct, kpis = self.change()
        self.assertEqual(pct, Decimal('-25.0'))
        self.assertMoney(kpis['prev_total_revenue'], '100.00')

    def test_no_sales_now(self):
        self.make_order('100.00', at=self.PREVIOUS)
        self.assertEqual(self.change()[0], Decimal('-100.0'))

    def test_none_when_the_previous_period_had_no_sales(self):
        self.make_order('150.00')
        pct, kpis = self.change()
        self.assertIsNone(pct)
        self.assertMoney(kpis['prev_total_revenue'], '0.00')

    def test_none_when_the_previous_period_only_had_cancelled_sales(self):
        self.make_order('100.00', status='cancelled', at=self.PREVIOUS)
        self.make_booking('10.00', status='cancelled', at=self.PREVIOUS)
        self.make_order('150.00')
        pct, kpis = self.change()
        self.assertIsNone(pct)
        self.assertMoney(kpis['prev_total_revenue'], '0.00')

    def test_none_when_nothing_was_ever_sold(self):
        self.assertIsNone(self.change()[0])

    def test_previous_twelve_months(self):
        self.make_order('200.00', at=local_dt(date(2024, 4, 1), 0, 30))
        self.make_order('50.00')
        kpis = self.overview('12m')['kpis']
        self.assertMoney(kpis['prev_total_revenue'], '200.00')
        self.assertEqual(kpis['revenue_change_pct'], Decimal('-75.0'))


# ---------------------------------------------------------------------------
# The revenue chart's numbers
# ---------------------------------------------------------------------------

class ChartBucketTests(FrozenClockCase):
    def chart(self, range_key):
        return self.overview(range_key)['chart']

    def point(self, chart, start):
        matches = [p for p in chart['points'] if p['start'] == start.isoformat()]
        self.assertEqual(len(matches), 1, f"no single bucket starts on {start}: {[p['start'] for p in chart['points']]}")
        return matches[0]

    def test_bucket_sizes_and_counts(self):
        expected = {'7d': ('day', 7), '30d': ('day', 30), '90d': ('week', 14), '12m': ('month', 12)}
        for range_key, (bucket, how_many) in expected.items():
            with self.subTest(range=range_key):
                chart = self.chart(range_key)
                self.assertEqual(chart['bucket'], bucket)
                self.assertEqual(len(chart['points']), how_many)

    def test_empty_buckets_are_present_with_zeros(self):
        for range_key in ('7d', '30d', '90d', '12m'):
            with self.subTest(range=range_key):
                chart = self.chart(range_key)
                self.assertIs(chart['has_data'], False)
                for point in chart['points']:
                    self.assertEqual(set(point), {'label', 'start', 'goods', 'delivery', 'total', 'orders'})
                    self.assertEqual((point['goods'], point['delivery'], point['total'], point['orders']), (0, 0, 0, 0))
                    self.assertTrue(point['label'])

    def test_daily_buckets_are_consecutive_local_days_ending_today(self):
        for range_key, days in (('7d', 7), ('30d', 30)):
            with self.subTest(range=range_key):
                starts = [p['start'] for p in self.chart(range_key)['points']]
                self.assertEqual(
                    starts, [(TODAY - timedelta(days=days - 1 - i)).isoformat() for i in range(days)])

    def test_weekly_buckets_start_on_mondays_and_cover_the_whole_period(self):
        points = self.chart('90d')['points']
        starts = [date.fromisoformat(p['start']) for p in points]
        period_start = TODAY - timedelta(days=89)
        # The first week is cut short by the period; either way of dating it is fine.
        self.assertIn(starts[0], (monday_of(period_start), period_start))
        self.assertEqual(starts[1:], [monday_of(period_start) + timedelta(weeks=i) for i in range(1, 14)])
        self.assertEqual(starts[-1], date(2026, 3, 9))

    def test_week_count_follows_the_calendar(self):
        # Ending on a Sunday, 90 days touch only 13 Monday-to-Sunday weeks.
        with freeze(local_dt(date(2026, 3, 15), 12)):
            points = self.chart('90d')['points']
        self.assertEqual(len(points), 13)
        self.assertEqual(points[-1]['start'], '2026-03-09')

    def test_monthly_buckets_are_the_twelve_calendar_months(self):
        starts = [p['start'] for p in self.chart('12m')['points']]
        self.assertEqual(starts, [d.isoformat() for d in month_starts(date(2025, 4, 1), 12)])

    def test_daily_bucketing_uses_the_local_day(self):
        day = TODAY - timedelta(days=3)
        self.make_order('12.50', at=local_dt(day, 0, 30))        # still the day before in UTC
        self.make_order('7.25', at=local_dt(day, 23, 30))
        self.make_booking('5.00', at=local_dt(day, 23, 59))
        self.make_order('99.00', status='cancelled', at=local_dt(day, 10))
        self.make_booking('99.00', status='cancelled', at=local_dt(day, 10))

        chart = self.chart('7d')
        self.assertIs(chart['has_data'], True)
        point = self.point(chart, day)
        self.assertEqual(point['goods'], 19.75)
        self.assertEqual(point['delivery'], 5.0)
        self.assertEqual(point['total'], 24.75)
        self.assertEqual(point['orders'], 2)
        for other in chart['points']:
            if other is not point:
                self.assertEqual(other['total'], 0)

    def test_weekly_bucketing_turns_over_at_local_midnight_on_monday(self):
        self.make_order('1.00', at=local_dt(date(2026, 3, 1), 23, 30))   # Sunday night
        self.make_order('2.00', at=local_dt(date(2026, 3, 2), 0, 30))    # Monday, still Sunday in UTC

        chart = self.chart('90d')
        self.assertEqual(self.point(chart, date(2026, 2, 23))['goods'], 1.0)
        self.assertEqual(self.point(chart, date(2026, 3, 2))['goods'], 2.0)

    def test_the_first_week_does_not_reach_back_before_the_period(self):
        period_start = TODAY - timedelta(days=89)                        # a Saturday
        self.make_order('1.00', at=local_dt(period_start, 0, 30))
        self.make_order('64.00', at=local_dt(period_start - timedelta(days=1), 23, 30))

        chart = self.chart('90d')
        self.assertEqual(chart['points'][0]['goods'], 1.0)
        self.assertEqual(sum(p['goods'] for p in chart['points']), 1.0)

    def test_monthly_bucketing_turns_over_at_local_midnight_on_the_first(self):
        self.make_order('1.00', at=local_dt(date(2026, 1, 31), 23, 30))
        self.make_order('2.00', at=local_dt(date(2026, 2, 1), 0, 30))    # still January in UTC
        self.make_booking('4.00', at=local_dt(date(2026, 2, 1), 0, 30))

        chart = self.chart('12m')
        january, february = self.point(chart, date(2026, 1, 1)), self.point(chart, date(2026, 2, 1))
        self.assertEqual((january['goods'], january['delivery'], january['orders']), (1.0, 0, 1))
        self.assertEqual((february['goods'], february['delivery'], february['total']), (2.0, 4.0, 6.0))

    def test_the_buckets_add_up_to_the_headline_figures(self):
        amounts = ['10.10', '20.20', '30.30', '0.05']
        for range_key in ('7d', '30d', '90d', '12m'):
            with self.subTest(range=range_key):
                Order.objects.all().delete()
                DeliveryBooking.objects.all().delete()
                start = self.overview(range_key)['period_start']
                span = (TODAY - start).days
                for i, amount in enumerate(amounts):
                    at = local_dt(start + timedelta(days=(span * i) // 3), 0, 5)
                    self.make_order(amount, at=at)
                    self.make_booking('5.00', at=at)
                self.make_order('77.00', status='cancelled')

                context = self.overview(range_key)
                points = context['chart']['points']
                self.assertAlmostEqual(sum(p['goods'] for p in points), 60.65, places=2)
                self.assertAlmostEqual(sum(p['delivery'] for p in points), 20.0, places=2)
                self.assertAlmostEqual(sum(p['total'] for p in points), 80.65, places=2)
                self.assertEqual(sum(p['orders'] for p in points), 4)
                self.assertMoney(context['kpis']['total_revenue'], '80.65')

    def test_chart_money_is_rounded_floats(self):
        self.make_order('0.10')
        self.make_order('0.20')
        point = self.chart('7d')['points'][-1]
        self.assertIsInstance(point['goods'], float)
        self.assertEqual(point['goods'], 0.3)
        self.assertEqual(point['total'], 0.3)

    def test_only_cancelled_sales_is_an_empty_chart(self):
        self.make_order('10.00', status='cancelled')
        self.make_booking('5.00', status='cancelled')
        self.assertIs(self.chart('7d')['has_data'], False)

    def test_the_page_carries_the_chart_json(self):
        self.make_order('10.00')
        response = self.staff_get('founder_dashboard')
        self.assertContains(response, 'id="revenue-chart-data"')


class TopProductsTests(FrozenClockCase):
    def test_ranked_by_revenue_at_the_price_actually_charged(self):
        # Sold at 10.00, then the shelf price went up: history must not be repriced.
        maize = self.make_product('Maize', price='99.00')
        oil = self.make_product('Oil', price='1.00')
        salt = self.make_product('Salt', price='1.00')
        self.make_order('200.00', items=[(maize, 20, '10.00')])
        self.make_order('80.00', status='delivered', items=[(oil, 4, '12.50'), (salt, 60, '0.50')])

        top = self.overview()['top_products']
        self.assertEqual([p['name'] for p in top], ['Maize', 'Oil', 'Salt'])
        self.assertEqual([p['product_id'] for p in top], [maize.id, oil.id, salt.id])
        self.assertEqual([p['units'] for p in top], [20, 4, 60])
        self.assertEqual([p['revenue'] for p in top], [Decimal('200.00'), Decimal('50.00'), Decimal('30.00')])
        self.assertEqual([p['share_pct'] for p in top], [100, 25, 15])
        for p in top:
            self.assertIsInstance(p['share_pct'], int)
            self.assertMoney(p['revenue'], p['revenue'])

    def test_sales_of_one_product_are_added_up_across_orders(self):
        maize, oil = self.make_product('Maize'), self.make_product('Oil')
        self.make_order('30.00', items=[(maize, 3, '10.00')])
        self.make_order('50.00', items=[(maize, 5, '10.00')])
        self.make_order('40.00', items=[(oil, 4, '10.00')])

        top = self.overview()['top_products']
        self.assertEqual([(p['name'], p['units'], p['revenue'], p['share_pct']) for p in top],
                         [('Maize', 8, Decimal('80.00'), 100), ('Oil', 4, Decimal('40.00'), 50)])

    def test_cancelled_and_out_of_period_sales_are_left_out(self):
        maize, oil, salt = self.make_product('Maize'), self.make_product('Oil'), self.make_product('Salt')
        self.make_order('10.00', items=[(maize, 1, '10.00')])
        self.make_order('900.00', status='cancelled', items=[(oil, 90, '10.00')])
        self.make_order('900.00', items=[(salt, 90, '10.00')], at=local_dt(TODAY - timedelta(days=7), 23, 30))

        top = self.overview('7d')['top_products']
        self.assertEqual([(p['name'], p['share_pct']) for p in top], [('Maize', 100)])

    def test_at_most_eight(self):
        for i in range(10):
            product = self.make_product(f'Product {i}')
            self.make_order('1.00', items=[(product, 1, f'{i + 1}.00')])

        top = self.overview()['top_products']
        self.assertEqual([p['name'] for p in top], [f'Product {i}' for i in range(9, 1, -1)])
        self.assertEqual(top[0]['share_pct'], 100)
        self.assertEqual(top[-1]['share_pct'], 30)

    def test_empty_without_sales(self):
        self.make_product('Maize')
        self.assertEqual(list(self.overview()['top_products']), [])


class OverviewListsTests(FrozenClockCase):
    def test_every_status_is_listed_even_at_zero(self):
        self.make_order(status='pending')
        self.make_order(status='pending')
        self.make_order(status='cancelled')
        self.make_order(status='delivered', at=local_dt(TODAY - timedelta(days=30), 12))
        self.make_booking(status='in_transit')
        self.make_booking(status='cancelled', at=local_dt(TODAY - timedelta(days=30), 12))

        context = self.overview('30d')
        self.assertEqual(
            [(row['status'], row['label'], row['count']) for row in context['orders_by_status']],
            [('pending', 'Pending', 2), ('processing', 'Processing', 0), ('shipped', 'Shipped', 0),
             ('delivered', 'Delivered', 0), ('cancelled', 'Cancelled', 1)],
        )
        self.assertEqual(
            [(row['status'], row['label'], row['count']) for row in context['deliveries_by_status']],
            [('pending', 'Pending', 0), ('confirmed', 'Confirmed', 0), ('in_transit', 'In transit', 1),
             ('delivered', 'Delivered', 0), ('cancelled', 'Cancelled', 0)],
        )

    def test_inventory_summary_and_nav_counts(self):
        self.make_product('Out', price='3.00', stock=0)
        self.make_product('Last one', price='3.00', stock=1)
        self.make_product('At the threshold', price='2.00', stock=5)
        self.make_product('Just above', price='1.50', stock=6)
        self.make_product('Plenty', price='0.10', stock=400)
        # Hidden wins over the stock level, and hidden stock is not for sale.
        self.make_product('Hidden and empty', price='50.00', stock=0, is_available=False)
        self.make_product('Hidden and full', price='50.00', stock=30, is_available=False)
        self.make_product('Hidden and low', price='50.00', stock=3, is_available=False)
        self.make_order(status='pending')
        self.make_order(status='processing')
        self.make_booking(status='pending')
        self.make_booking(status='pending')
        self.make_booking(status='confirmed')
        ContactMessage.objects.create(name='A', subject='s', message='m')
        ContactMessage.objects.create(name='B', subject='s', message='m', status='replied')

        context = self.overview()
        inventory = context['inventory']
        self.assertEqual(
            {key: inventory[key] for key in ('total', 'in_stock', 'low_stock', 'out_of_stock', 'hidden')},
            {'total': 8, 'in_stock': 2, 'low_stock': 2, 'out_of_stock': 1, 'hidden': 3},
        )
        self.assertMoney(inventory['retail_value'], '62.00')
        nav = context['nav']
        self.assertEqual(nav['active'], 'overview')
        self.assertEqual(
            (nav['out_of_stock'], nav['low_stock'], nav['pending_orders'], nav['pending_deliveries'], nav['open_messages']),
            (1, 2, 1, 2, 1),
        )

    def test_retail_value_of_an_empty_catalogue_is_zero(self):
        self.assertMoney(self.overview()['inventory']['retail_value'], '0.00')

    def test_stock_alerts_are_the_available_products_running_out(self):
        self.make_product('Zebra salt', stock=0)
        self.make_product('Apple juice', stock=0)
        self.make_product('Rice', stock=5)
        self.make_product('Beans', stock=2)
        self.make_product('Plenty', stock=6)
        self.make_product('Hidden', stock=0, is_available=False)
        self.make_product('Hidden and low', stock=3, is_available=False)

        alerts = list(self.overview()['stock_alerts'])
        self.assertEqual([p.name for p in alerts], ['Apple juice', 'Zebra salt', 'Beans', 'Rice'])

    def test_stock_alerts_show_at_most_eight(self):
        for i in range(10):
            self.make_product(f'Low {i}', stock=1)
        self.assertEqual(len(self.overview()['stock_alerts']), 8)

    def test_upcoming_deliveries_are_open_bookings_from_today_in_delivery_order(self):
        tomorrow = TODAY + timedelta(days=1)
        self.make_booking(delivery_date=tomorrow, time_slot='morning', delivery_address='tomorrow morning')
        self.make_booking(delivery_date=TODAY, time_slot='evening', status='in_transit', delivery_address='today evening')
        self.make_booking(delivery_date=TODAY, time_slot='morning', status='confirmed', delivery_address='today morning')
        self.make_booking(delivery_date=TODAY, time_slot='afternoon', delivery_address='today afternoon')
        self.make_booking(delivery_date=TODAY - timedelta(days=1), delivery_address='yesterday')
        self.make_booking(delivery_date=tomorrow, status='delivered', delivery_address='done')
        self.make_booking(delivery_date=tomorrow, status='cancelled', delivery_address='cancelled')

        upcoming = [b.delivery_address for b in self.overview()['upcoming_deliveries']]
        self.assertEqual(upcoming, ['today morning', 'today afternoon', 'today evening', 'tomorrow morning'])

    def test_upcoming_deliveries_use_the_local_date_just_after_midnight(self):
        self.make_booking(delivery_date=TODAY - timedelta(days=1), delivery_address='yesterday')
        self.make_booking(delivery_date=TODAY, delivery_address='today')
        with freeze(local_dt(TODAY, 0, 30)):
            context = self.overview()
        self.assertEqual([b.delivery_address for b in context['upcoming_deliveries']], ['today'])

    def test_short_lists_are_capped(self):
        for i in range(8):
            self.make_order(at=local_dt(TODAY - timedelta(days=i), 12))
            self.make_booking(delivery_date=TODAY + timedelta(days=i))
            ContactMessage.objects.create(name=f'Sender {i}', subject='s', message='m')

        context = self.overview()
        self.assertEqual(len(context['upcoming_deliveries']), 6)
        self.assertEqual(len(context['awaiting_messages']), 4)
        recent = list(context['recent_orders'])
        self.assertEqual(len(recent), 6)
        self.assertEqual(recent, list(Order.objects.order_by('-created_at')[:6]))

    def test_awaiting_messages_are_the_newest_open_ones(self):
        def message(subject, days_ago, status='open'):
            created = ContactMessage.objects.create(name='Sender', subject=subject, message='m', status=status)
            ContactMessage.objects.filter(pk=created.pk).update(created_at=local_dt(TODAY - timedelta(days=days_ago)))

        for days_ago in range(1, 6):
            message(f'open {days_ago}', days_ago)
        # Answered since, and newer than every open one: a list that forgot the
        # status would show these first.
        message('replied', 0, status='replied')
        message('resolved', 0, status='resolved')

        awaiting = list(self.overview()['awaiting_messages'])
        self.assertEqual([m.subject for m in awaiting], ['open 1', 'open 2', 'open 3', 'open 4'])
        self.assertEqual({m.status for m in awaiting}, {'open'})


# ---------------------------------------------------------------------------
# Stock: received, corrected, hidden
# ---------------------------------------------------------------------------

class RestockTests(DashboardContractCase):
    def setUp(self):
        self.product = self.make_product(stock=5, supplier='National Foods')

    def test_restock_adds_to_stock_and_logs_the_delivery(self):
        response = self.staff_post('dashboard_restock', [self.product.id],
                                   quantity='10', unit_cost='1.50', note='Invoice 4471')

        self.assertEqual(response.status_code, 302)
        self.assertFlashLevel(response, flash_levels.SUCCESS)
        self.assertEqual(self.stock_of(self.product), 15)
        entry = StockEntry.objects.get()
        self.assertEqual(
            (entry.product, entry.kind, entry.quantity, entry.unit_cost, entry.note, entry.stock_after, entry.created_by),
            (self.product, 'restock', 10, Decimal('1.50'), 'Invoice 4471', 15, self.staff),
        )
        # Nothing typed in: the product's usual supplier is assumed.
        self.assertEqual(entry.supplier, 'National Foods')
        self.assertEqual(entry.total_cost, Decimal('15.00'))

    def test_restock_without_a_cost_and_with_another_supplier(self):
        self.staff_post('dashboard_restock', [self.product.id], quantity='3', supplier='Blue Ribbon')

        entry = StockEntry.objects.get()
        self.assertIsNone(entry.unit_cost)
        self.assertIsNone(entry.total_cost)
        self.assertEqual(entry.supplier, 'Blue Ribbon')
        self.assertEqual(self.stock_of(self.product), 8)

    def test_each_restock_records_the_level_it_left_behind(self):
        self.staff_post('dashboard_restock', [self.product.id], quantity='10')
        self.staff_post('dashboard_restock', [self.product.id], quantity='3')
        other = self.make_product('Other', stock=100)
        self.staff_post('dashboard_restock', [other.id], quantity='1')

        self.assertEqual(self.stock_of(self.product), 18)
        self.assertEqual(self.stock_of(other), 101)
        self.assertEqual(
            list(StockEntry.objects.order_by('id').values_list('product_id', 'quantity', 'stock_after')),
            [(self.product.id, 10, 15), (self.product.id, 3, 18), (other.id, 1, 101)],
        )

    def test_restock_builds_on_the_stock_in_the_database(self):
        # A sale between loading the page and pressing the button must not be undone.
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=2)
        self.staff_post('dashboard_restock', [self.product.id], quantity='10')

        self.assertEqual(self.stock_of(self.product), 12)
        self.assertEqual(StockEntry.objects.get().stock_after, 12)

    def test_a_hidden_or_sold_out_product_can_be_restocked(self):
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=0, is_available=False)
        self.staff_post('dashboard_restock', [self.product.id], quantity='4')

        self.assertEqual(self.stock_of(self.product), 4)
        self.assertFalse(Product.objects.get(pk=self.product.pk).is_available)

    def test_invalid_restocks_change_nothing(self):
        for data in ({'quantity': '0'}, {'quantity': '-5'}, {'quantity': ''}, {}, {'quantity': 'ten'},
                     {'quantity': '2.5'}, {'quantity': '5', 'unit_cost': '-1.00'}, {'quantity': '5', 'unit_cost': 'cheap'}):
            with self.subTest(data=data):
                response = self.staff_post('dashboard_restock', [self.product.id], **data)
                self.assertEqual(response.status_code, 302)
                self.assertFlashLevel(response, flash_levels.ERROR)
                self.assertEqual(self.stock_of(self.product), 5)
                self.assertFalse(StockEntry.objects.exists())


class AdjustStockTests(DashboardContractCase):
    def setUp(self):
        self.product = self.make_product(stock=10)

    def test_a_correction_down_logs_the_negative_difference(self):
        response = self.staff_post('dashboard_adjust_stock', [self.product.id], new_quantity='3', note='Two bags burst')

        self.assertEqual(response.status_code, 302)
        self.assertFlashLevel(response, flash_levels.SUCCESS)
        self.assertEqual(self.stock_of(self.product), 3)
        entry = StockEntry.objects.get()
        self.assertEqual(
            (entry.product, entry.kind, entry.quantity, entry.note, entry.stock_after, entry.created_by),
            (self.product, 'adjustment', -7, 'Two bags burst', 3, self.staff),
        )
        self.assertIsNone(entry.unit_cost)

    def test_a_correction_up_logs_the_positive_difference(self):
        self.staff_post('dashboard_adjust_stock', [self.product.id], new_quantity='14')

        self.assertEqual(self.stock_of(self.product), 14)
        entry = StockEntry.objects.get()
        self.assertEqual((entry.kind, entry.quantity, entry.stock_after), ('adjustment', 4, 14))

    def test_a_correction_to_zero(self):
        self.staff_post('dashboard_adjust_stock', [self.product.id], new_quantity='0')

        self.assertEqual(self.stock_of(self.product), 0)
        entry = StockEntry.objects.get()
        self.assertEqual((entry.quantity, entry.stock_after), (-10, 0))

    def test_the_difference_is_measured_against_the_database(self):
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=8)
        self.staff_post('dashboard_adjust_stock', [self.product.id], new_quantity='6')

        self.assertEqual(self.stock_of(self.product), 6)
        self.assertEqual(StockEntry.objects.get().quantity, -2)

    def test_the_same_quantity_does_nothing_and_says_so(self):
        response = self.staff_post('dashboard_adjust_stock', [self.product.id], new_quantity='10', note='recount')

        self.assertEqual(response.status_code, 302)
        levels = [m.level for m in self.flashes(response)]
        self.assertEqual(len(levels), 1)
        self.assertNotEqual(levels[0], flash_levels.SUCCESS)
        self.assertEqual(self.stock_of(self.product), 10)
        self.assertFalse(StockEntry.objects.exists())

    def test_invalid_corrections_change_nothing(self):
        for data in ({'new_quantity': '-1'}, {'new_quantity': ''}, {}, {'new_quantity': 'none'}, {'new_quantity': '1.5'}):
            with self.subTest(data=data):
                response = self.staff_post('dashboard_adjust_stock', [self.product.id], **data)
                self.assertEqual(response.status_code, 302)
                self.assertFlashLevel(response, flash_levels.ERROR)
                self.assertEqual(self.stock_of(self.product), 10)
                self.assertFalse(StockEntry.objects.exists())


class ProductFormTests(DashboardContractCase):
    def form_data(self, **overrides):
        data = {'name': 'Mazoe Orange Crush 2L', 'description': 'Cordial', 'category': self.category.id,
                'price': '4.50', 'image': '', 'supplier': 'Schweppes', 'is_local_product': 'on',
                'is_available': 'on', 'opening_stock': '12'}
        data.update(overrides)
        return data

    def post_ok(self, url_name, args=(), /, **data):
        response = self.staff_post(url_name, args, **data)
        if response.status_code != 302:
            self.fail(f'form was rejected: {response.context["form"].errors.as_json()}')
        return response

    def test_adding_a_product_with_opening_stock_logs_it(self):
        self.post_ok('dashboard_product_add', **self.form_data())

        product = Product.objects.get(name='Mazoe Orange Crush 2L')
        self.assertEqual((product.stock_quantity, product.price, product.supplier, product.is_available),
                         (12, Decimal('4.50'), 'Schweppes', True))
        entry = StockEntry.objects.get()
        self.assertEqual(
            (entry.product, entry.kind, entry.quantity, entry.note, entry.stock_after, entry.created_by),
            (product, 'restock', 12, 'Opening stock', 12, self.staff),
        )

    def test_adding_a_product_without_opening_stock_logs_nothing(self):
        self.post_ok('dashboard_product_add', **self.form_data(opening_stock='0'))

        self.assertEqual(Product.objects.get(name='Mazoe Orange Crush 2L').stock_quantity, 0)
        self.assertFalse(StockEntry.objects.exists())

    def test_an_invalid_product_is_not_saved(self):
        for overrides in ({'price': '-1'}, {'name': ''}, {'opening_stock': '-3'}, {'category': ''}):
            with self.subTest(overrides=overrides):
                response = self.staff_post('dashboard_product_add', **self.form_data(**overrides))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertFalse(Product.objects.exists())
        self.assertFalse(StockEntry.objects.exists())

    def test_editing_a_product_never_touches_its_stock(self):
        product = self.make_product(stock=7)
        page = self.staff_get('dashboard_product_edit', [product.id])
        self.assertNotIn('opening_stock', page.context['form'].fields)
        self.assertNotIn('stock_quantity', page.context['form'].fields)

        # Stock only moves through restocks and corrections, which leave a trail.
        self.post_ok('dashboard_product_edit', [product.id],
                     **self.form_data(name='Renamed', price='9.99', opening_stock='99', stock_quantity='99'))

        product.refresh_from_db()
        self.assertEqual((product.name, product.price, product.stock_quantity), ('Renamed', Decimal('9.99'), 7))
        self.assertFalse(StockEntry.objects.exists())

    def test_a_sale_that_lands_while_a_product_is_being_saved_is_kept(self):
        product = self.make_product(stock=7)

        def sell_two(sender, instance, **kwargs):
            # Checkout takes stock with an F() update, exactly like this.
            pre_save.disconnect(sell_two, sender=Product)
            Product.objects.filter(pk=instance.pk).update(stock_quantity=F('stock_quantity') - 2)

        pre_save.connect(sell_two, sender=Product)
        self.addCleanup(pre_save.disconnect, sell_two, sender=Product)
        self.post_ok('dashboard_product_edit', [product.id], **self.form_data(name='Renamed'))

        product.refresh_from_db()
        self.assertEqual((product.name, product.stock_quantity), ('Renamed', 5))

    def test_edit_page_offers_the_stock_forms_and_the_last_ten_entries(self):
        product = self.make_product(stock=7)
        other = self.make_product('Other')
        for i in range(12):
            self.make_entry(product, i + 1)
        self.make_entry(other, 500)

        context = self.staff_get('dashboard_product_edit', [product.id]).context
        self.assertEqual(context['product'], product)
        self.assertIn('quantity', context['restock_form'].fields)
        self.assertIn('new_quantity', context['adjust_form'].fields)
        entries = list(context['entries'])
        self.assertEqual(len(entries), 10)
        self.assertTrue(all(entry.product_id == product.id for entry in entries))
        self.assertEqual(entries[0].quantity, 12)

    def test_add_page_has_no_stock_forms(self):
        context = self.staff_get('dashboard_product_add').context
        self.assertIsNone(context['product'])
        self.assertIn('opening_stock', context['form'].fields)

    def test_hiding_and_showing_a_product(self):
        product = self.make_product(stock=7)

        response = self.staff_post('dashboard_toggle_available', [product.id])
        self.assertEqual(response.json(), {'success': True, 'is_available': False})
        self.assertFalse(Product.objects.get(pk=product.pk).is_available)

        response = self.staff_post('dashboard_toggle_available', [product.id])
        self.assertEqual(response.json(), {'success': True, 'is_available': True})
        product.refresh_from_db()
        self.assertTrue(product.is_available)
        self.assertEqual(product.stock_quantity, 7)


class InventoryPageTests(DashboardContractCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        drinks = Category.objects.create(name='Drinks')
        make = lambda name, stock, **extra: Product.objects.create(  # noqa: E731
            name=name, description='x', price=Decimal('2.00'), stock_quantity=stock,
            category=extra.pop('category', cls.category), **extra)
        cls.out = make('Sugar', 0, supplier='Star Africa')
        cls.low_one = make('Salt', 1)
        cls.low_five = make('Rice', 5)
        cls.in_six = make('Flour', 6)
        cls.plenty = make('Cola', 40, category=drinks, supplier='Delta')
        cls.hidden_empty = make('Old tea', 0, is_available=False)
        cls.hidden_full = make('Old coffee', 10, is_available=False, category=drinks)
        # Hidden wins over every stock level; 1 to 5 is the one "low" would also claim.
        cls.hidden_low = make('Old jam', 3, is_available=False)
        cls.drinks = drinks

    def names(self, **params):
        return sorted(p.name for p in self.staff_get('dashboard_inventory', **params).context['products'])

    def test_counts_and_default_view(self):
        context = self.staff_get('dashboard_inventory').context
        self.assertEqual(context['active_filter'], 'all')
        self.assertEqual(context['sort'], 'stock_low')
        self.assertEqual(context['counts'], {'all': 8, 'in': 2, 'low': 2, 'out': 1, 'hidden': 3})
        self.assertEqual(len(context['products']), 8)
        self.assertEqual(context['nav']['active'], 'inventory')
        self.assertEqual(context['inventory']['out_of_stock'], 1)
        self.assertEqual(context['inventory']['retail_value'], Decimal('104.00'))

    def test_each_filter_lists_its_own_stock_state(self):
        expected = {
            'in': ['Cola', 'Flour'], 'low': ['Rice', 'Salt'], 'out': ['Sugar'],
            'hidden': ['Old coffee', 'Old jam', 'Old tea'],
        }
        for key, names in expected.items():
            with self.subTest(filter=key):
                self.assertEqual(self.names(filter=key), names)
        self.assertEqual(self.staff_get('dashboard_inventory', filter='bogus').context['active_filter'], 'all')

    def test_every_listed_product_agrees_with_its_stock_state(self):
        for key in ('in', 'low', 'out', 'hidden'):
            for product in self.staff_get('dashboard_inventory', filter=key).context['products']:
                self.assertEqual(product.stock_state, key)

    def test_search_covers_name_supplier_and_category(self):
        self.assertEqual(self.names(search='sug'), ['Sugar'])
        self.assertEqual(self.names(search='delta'), ['Cola'])
        self.assertEqual(self.names(search='drinks'), ['Cola', 'Old coffee'])
        self.assertEqual(self.names(category=str(self.drinks.id)), ['Cola', 'Old coffee'])
        self.assertEqual(self.names(search='nothing like this'), [])

    def test_sorting(self):
        ordered = lambda sort: [p.stock_quantity for p in  # noqa: E731
                                self.staff_get('dashboard_inventory', sort=sort).context['products']]
        self.assertEqual(ordered('stock_low'), [0, 0, 1, 3, 5, 6, 10, 40])
        self.assertEqual(ordered('stock_high'), [40, 10, 6, 5, 3, 1, 0, 0])
        self.assertEqual(self.staff_get('dashboard_inventory', sort='bogus').context['sort'], 'stock_low')

    def test_units_sold_are_all_time_without_cancelled_orders(self):
        self.make_order(items=[(self.plenty, 2, '2.00')], at=local_dt(date(2020, 1, 1)))
        self.make_order(items=[(self.plenty, 3, '2.00')], status='delivered')
        self.make_order(items=[(self.plenty, 50, '2.00')], status='cancelled')
        # Stock entries on the same product must not multiply the sales figure.
        for _ in range(3):
            self.make_entry(self.plenty, 10, '1.00')

        by_name = {p.name: p.units_sold for p in self.staff_get('dashboard_inventory').context['products']}
        self.assertEqual(by_name['Cola'], 5)
        self.assertEqual(by_name['Sugar'], 0)

    def test_pages_hold_24_products(self):
        for i in range(20):
            Product.objects.create(name=f'Bulk {i}', description='x', category=self.category, price=Decimal('1.00'))
        context = self.staff_get('dashboard_inventory').context
        self.assertEqual(len(context['products']), 24)
        self.assertEqual(context['products'].paginator.count, 28)
        self.assertEqual(len(self.staff_get('dashboard_inventory', page=2).context['products']), 4)


class StockHistoryTests(DashboardContractCase):
    def setUp(self):
        self.maize, self.oil = self.make_product('Maize'), self.make_product('Oil')
        self.make_entry(self.maize, 10, '1.25')
        self.make_entry(self.maize, 40)
        self.make_entry(self.maize, -3, kind='adjustment')
        self.make_entry(self.oil, 6, '2.00')
        self.make_entry(self.oil, 2, '9.00', kind='adjustment')

    def test_totals_count_restocks_only_and_cost_only_where_known(self):
        context = self.staff_get('dashboard_stock_history').context
        self.assertEqual(context['active_kind'], 'all')
        self.assertIsNone(context['product'])
        self.assertEqual(context['counts'], {'all': 5, 'restock': 3, 'adjustment': 2})
        self.assertEqual(len(context['entries']), 5)
        self.assertEqual(context['totals']['units_in'], 56)
        self.assertMoney(context['totals']['cost'], '24.50')

    def test_totals_follow_the_product_filter(self):
        context = self.staff_get('dashboard_stock_history', product=self.maize.id).context
        self.assertEqual(context['product'], self.maize)
        self.assertEqual(len(context['entries']), 3)
        self.assertEqual(context['totals']['units_in'], 50)
        self.assertMoney(context['totals']['cost'], '12.50')

    def test_kind_filter(self):
        context = self.staff_get('dashboard_stock_history', kind='adjustment').context
        self.assertEqual(context['active_kind'], 'adjustment')
        self.assertEqual({entry.kind for entry in context['entries']}, {'adjustment'})
        self.assertEqual(context['totals']['units_in'], 0)
        self.assertMoney(context['totals']['cost'], '0.00')

        context = self.staff_get('dashboard_stock_history', kind='restock').context
        self.assertEqual(len(context['entries']), 3)
        self.assertEqual(self.staff_get('dashboard_stock_history', kind='bogus').context['active_kind'], 'all')

    def test_pages_hold_30_entries(self):
        for _ in range(30):
            self.make_entry(self.oil, 1)
        context = self.staff_get('dashboard_stock_history').context
        self.assertEqual(len(context['entries']), 30)
        self.assertEqual(context['entries'].paginator.count, 35)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderStatusTests(DashboardContractCase):
    def setUp(self):
        self.maize = self.make_product('Maize', stock=10)
        self.oil = self.make_product('Oil', stock=0)
        self.order = self.make_order('35.00', items=[(self.maize, 2, '10.00'), (self.oil, 3, '5.00')])

    def set_status(self, status, order=None, **extra):
        return self.staff_post('dashboard_order_status', [(order or self.order).id], status=status, **extra)

    def status_of(self, obj):
        return type(obj).objects.get(pk=obj.pk).status

    def test_cancelling_returns_every_item_to_stock(self):
        response = self.set_status('cancelled')

        self.assertEqual(response.status_code, 302)
        self.assertFlashLevel(response, flash_levels.SUCCESS)
        self.assertEqual(self.status_of(self.order), 'cancelled')
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))

    def test_cancelling_twice_returns_stock_once(self):
        self.set_status('cancelled')
        response = self.set_status('cancelled')

        # "Same status" (info) and "cancelled is final" (error) both apply here.
        self.assertIn([m.level for m in self.flashes(response)], ([flash_levels.INFO], [flash_levels.ERROR]))
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))

    def test_the_same_product_on_two_lines_is_returned_in_full(self):
        order = self.make_order('30.00', items=[(self.maize, 1, '10.00'), (self.maize, 2, '10.00')])
        self.set_status('cancelled', order)
        self.assertEqual(self.stock_of(self.maize), 13)

    def test_only_the_cancelled_orders_items_come_back(self):
        other = self.make_order('50.00', items=[(self.maize, 5, '10.00')])
        self.set_status('cancelled')

        self.assertEqual(self.stock_of(self.maize), 12)
        self.assertEqual(self.status_of(other), 'pending')

    def test_a_cancelled_order_is_final(self):
        self.set_status('cancelled')
        for status in ('pending', 'processing', 'shipped', 'delivered'):
            with self.subTest(status=status):
                response = self.set_status(status)
                self.assertFlashLevel(response, flash_levels.ERROR)
                self.assertEqual(self.status_of(self.order), 'cancelled')
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))

    def test_an_order_cancelled_elsewhere_gives_no_stock_back(self):
        # Whatever cancelled it has already dealt with the stock.
        Order.objects.filter(pk=self.order.pk).update(status='cancelled')
        response = self.set_status('cancelled')

        self.assertEqual(len(self.flashes(response)), 1)
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (10, 0))

    def test_the_customer_cannot_cancel_again_after_staff_did(self):
        self.set_status('cancelled')
        self.client.force_login(self.customer)
        self.client.post(reverse('cancel_order', args=[self.order.id]))

        self.assertEqual(self.status_of(self.order), 'cancelled')
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))

    def test_an_order_the_customer_cancelled_is_gone_from_revenue_and_from_staff(self):
        self.make_booking('5.00', order=self.order)
        self.client.force_login(self.customer)
        self.client.post(reverse('cancel_order', args=[self.order.id]))

        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))
        self.assertEqual(self.set_status('cancelled').status_code, 404)
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))
        kpis = self.overview()['kpis']
        self.assertMoney(kpis['total_revenue'], '0.00')
        self.assertEqual(kpis['orders_count'], 0)

    def test_cancelling_cancels_only_the_bookings_still_on_their_way(self):
        pending = self.make_booking(order=self.order, status='pending')
        confirmed = self.make_booking(order=self.order, status='confirmed')
        in_transit = self.make_booking(order=self.order, status='in_transit')
        delivered = self.make_booking(order=self.order, status='delivered')
        already = self.make_booking(order=self.order, status='cancelled',
                                    cancellation_reason='customer_request', cancellation_notes='Changed my mind')
        elsewhere = self.make_booking(order=self.make_order(), status='pending')
        standalone = self.make_booking(order=None, status='pending')

        self.set_status('cancelled')

        for booking in (pending, confirmed, in_transit):
            booking.refresh_from_db()
            self.assertEqual(
                (booking.status, booking.cancellation_reason, booking.cancellation_notes),
                ('cancelled', 'other', 'Order cancelled by staff'),
            )
            self.assertIsNotNone(booking.cancelled_at)
        delivered.refresh_from_db()
        self.assertEqual((delivered.status, delivered.cancellation_reason, delivered.cancelled_at), ('delivered', '', None))
        already.refresh_from_db()
        self.assertEqual((already.cancellation_reason, already.cancellation_notes), ('customer_request', 'Changed my mind'))
        self.assertEqual(self.status_of(elsewhere), 'pending')
        self.assertEqual(self.status_of(standalone), 'pending')

    def test_a_delivered_order_can_still_be_cancelled_and_restocked(self):
        Order.objects.filter(pk=self.order.pk).update(status='delivered')
        self.set_status('cancelled')

        self.assertEqual(self.status_of(self.order), 'cancelled')
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (12, 3))

    def test_cancelling_takes_the_order_and_its_delivery_fee_out_of_revenue(self):
        self.make_booking('5.00', order=self.order)
        keep = self.make_order('20.00')
        self.make_booking('10.00', order=keep, status='delivered')
        self.assertMoney(self.overview()['kpis']['total_revenue'], '70.00')

        self.set_status('cancelled')

        kpis = self.overview()['kpis']
        self.assertMoney(kpis['goods_revenue'], '20.00')
        self.assertMoney(kpis['delivery_revenue'], '10.00')
        self.assertMoney(kpis['total_revenue'], '30.00')
        self.assertEqual(kpis['units_sold'], 0)

    def test_unknown_status_is_refused(self):
        for status in ('refunded', '', 'CANCELLED', 'in_transit'):
            with self.subTest(status=status):
                response = self.set_status(status)
                self.assertEqual(response.status_code, 302)
                self.assertFlashLevel(response, flash_levels.ERROR)
                self.assertEqual(self.status_of(self.order), 'pending')
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (10, 0))

    def test_missing_status_is_refused(self):
        response = self.staff_post('dashboard_order_status', [self.order.id])
        self.assertFlashLevel(response, flash_levels.ERROR)
        self.assertEqual(self.status_of(self.order), 'pending')

    def test_same_status_changes_nothing(self):
        response = self.set_status('pending')
        self.assertFlashLevel(response, flash_levels.INFO)
        self.assertEqual(self.status_of(self.order), 'pending')

    def test_staff_can_move_an_order_in_either_direction(self):
        booking = self.make_booking(order=self.order, status='confirmed')
        for status in ('processing', 'shipped', 'delivered', 'pending', 'delivered', 'processing'):
            with self.subTest(status=status):
                response = self.set_status(status)
                self.assertFlashLevel(response, flash_levels.SUCCESS)
                self.assertEqual(self.status_of(self.order), status)
        # None of that is a cancellation: stock and the delivery stay as they were.
        self.assertEqual((self.stock_of(self.maize), self.stock_of(self.oil)), (10, 0))
        self.assertEqual(self.status_of(booking), 'confirmed')


class OrderPagesTests(DashboardContractCase):
    def setUp(self):
        self.maize = self.make_product('Maize')
        rudo = User.objects.create_user('rudo', password='pw', first_name='Rudo', last_name='Dube')
        self.first = self.make_order('20.00', items=[(self.maize, 2, '5.00'), (self.maize, 3, '5.00')])
        self.second = self.make_order('9.00', status='delivered', user=rudo)
        self.third = self.make_order('1.00', status='cancelled', user=rudo)
        Order.objects.filter(pk=self.second.pk).update(delivery_city='Gweru', delivery_phone='0719999999')

    def test_list_counts_filters_and_item_totals(self):
        context = self.staff_get('dashboard_orders').context
        self.assertEqual(context['active_status'], 'all')
        self.assertEqual(context['counts'], {'all': 3, 'pending': 1, 'processing': 0, 'shipped': 0,
                                             'delivered': 1, 'cancelled': 1})
        self.assertEqual(list(context['status_choices']), list(Order.STATUS_CHOICES))
        self.assertEqual(context['nav']['active'], 'orders')
        by_id = {order.id: order for order in context['orders']}
        self.assertEqual(by_id[self.first.id].item_count, 5)
        self.assertFalse(by_id[self.second.id].item_count)

        delivered = self.staff_get('dashboard_orders', status='delivered').context
        self.assertEqual(delivered['active_status'], 'delivered')
        self.assertEqual([order.id for order in delivered['orders']], [self.second.id])
        self.assertEqual(self.staff_get('dashboard_orders', status='bogus').context['active_status'], 'all')

    def test_search(self):
        found = lambda term: {o.id for o in self.staff_get('dashboard_orders', search=term).context['orders']}  # noqa: E731
        self.assertEqual(found(self.first.order_number), {self.first.id})
        self.assertEqual(found('rudo'), {self.second.id, self.third.id})
        self.assertEqual(found('Moyo'), {self.first.id})
        self.assertEqual(found('0719999999'), {self.second.id})
        self.assertEqual(found('gweru'), {self.second.id})
        self.assertEqual(self.staff_get('dashboard_orders', search='gweru').context['search_query'], 'gweru')

    def test_pages_hold_20_orders(self):
        for _ in range(20):
            self.make_order()
        self.assertEqual(len(self.staff_get('dashboard_orders').context['orders']), 20)

    def test_detail_shows_the_newest_booking(self):
        self.make_booking(order=self.first, status='cancelled', at=local_dt(date(2026, 1, 1)))
        newest = self.make_booking(order=self.first, status='confirmed', at=local_dt(date(2026, 1, 2)))

        context = self.staff_get('dashboard_order_detail', [self.first.id]).context
        self.assertEqual(context['order'], self.first)
        self.assertEqual(len(context['items']), 2)
        self.assertEqual(context['delivery'], newest)
        self.assertIs(context['can_change_status'], True)
        self.assertEqual(list(context['status_choices']), list(Order.STATUS_CHOICES))

    def test_detail_of_a_cancelled_order_without_a_booking(self):
        context = self.staff_get('dashboard_order_detail', [self.third.id]).context
        self.assertIsNone(context['delivery'])
        self.assertIs(context['can_change_status'], False)


# ---------------------------------------------------------------------------
# Deliveries
# ---------------------------------------------------------------------------

class DeliveryStatusTests(DashboardContractCase):
    def setUp(self):
        self.maize = self.make_product('Maize', stock=10)
        self.order = self.make_order('20.00', items=[(self.maize, 2, '10.00')])
        self.booking = self.make_booking('5.00', order=self.order)

    def set_status(self, status, booking=None, **extra):
        return self.staff_post('dashboard_delivery_status', [(booking or self.booking).id], status=status, **extra)

    def state(self):
        return (DeliveryBooking.objects.get(pk=self.booking.pk).status, Order.objects.get(pk=self.order.pk).status)

    def test_in_transit_ships_an_order_that_has_not_left_yet(self):
        for order_status in ('pending', 'processing'):
            with self.subTest(order_status=order_status):
                Order.objects.filter(pk=self.order.pk).update(status=order_status)
                DeliveryBooking.objects.filter(pk=self.booking.pk).update(status='confirmed')
                response = self.set_status('in_transit')

                self.assertEqual(self.state(), ('in_transit', 'shipped'))
                self.assertFlashLevel(response, flash_levels.SUCCESS)
                self.assertIn('order', str(self.flashes(response)[0]).lower())

    def test_in_transit_leaves_other_orders_alone(self):
        for order_status in ('shipped', 'delivered', 'cancelled'):
            with self.subTest(order_status=order_status):
                Order.objects.filter(pk=self.order.pk).update(status=order_status)
                DeliveryBooking.objects.filter(pk=self.booking.pk).update(status='confirmed')
                self.set_status('in_transit')
                self.assertEqual(self.state(), ('in_transit', order_status))

    def test_delivered_delivers_the_order(self):
        for order_status in ('pending', 'processing', 'shipped', 'delivered'):
            with self.subTest(order_status=order_status):
                Order.objects.filter(pk=self.order.pk).update(status=order_status)
                DeliveryBooking.objects.filter(pk=self.booking.pk).update(status='in_transit')
                self.set_status('delivered')
                self.assertEqual(self.state(), ('delivered', 'delivered'))

    def test_a_delivery_never_resurrects_a_cancelled_order(self):
        Order.objects.filter(pk=self.order.pk).update(status='cancelled')
        for status in ('confirmed', 'in_transit', 'delivered'):
            with self.subTest(status=status):
                self.set_status(status)
                self.assertEqual(self.state(), (status, 'cancelled'))
        self.assertEqual(self.stock_of(self.maize), 10)

    def test_confirming_or_resetting_a_delivery_does_not_touch_the_order(self):
        Order.objects.filter(pk=self.order.pk).update(status='processing')
        self.set_status('confirmed')
        self.assertEqual(self.state(), ('confirmed', 'processing'))
        self.set_status('pending')
        self.assertEqual(self.state(), ('pending', 'processing'))

    def test_moving_a_delivery_back_does_not_move_the_order_back(self):
        self.set_status('delivered')
        self.set_status('confirmed')
        self.assertEqual(self.state(), ('confirmed', 'delivered'))

    def test_cancelling_a_delivery_keeps_the_order_and_its_stock(self):
        response = self.set_status('cancelled')

        self.assertFlashLevel(response, flash_levels.SUCCESS)
        booking = DeliveryBooking.objects.get(pk=self.booking.pk)
        self.assertEqual((booking.status, booking.cancellation_reason, booking.cancellation_notes),
                         ('cancelled', 'other', 'Cancelled by staff'))
        self.assertIsNotNone(booking.cancelled_at)
        self.assertEqual(Order.objects.get(pk=self.order.pk).status, 'pending')
        self.assertEqual(self.stock_of(self.maize), 10)

    def test_a_cancelled_delivery_is_final_and_cannot_move_its_order(self):
        self.set_status('cancelled')
        for status in ('pending', 'confirmed', 'in_transit', 'delivered', 'cancelled'):
            with self.subTest(status=status):
                response = self.set_status(status)
                allowed = [[flash_levels.ERROR]] + ([[flash_levels.INFO]] if status == 'cancelled' else [])
                self.assertIn([m.level for m in self.flashes(response)], allowed)
                self.assertEqual(self.state(), ('cancelled', 'pending'))
        # The customer's own reason must survive a second cancel as well.
        self.assertEqual(DeliveryBooking.objects.get(pk=self.booking.pk).cancellation_notes, 'Cancelled by staff')

    def test_unknown_and_missing_status_are_refused(self):
        for data in ({'status': 'lost'}, {'status': ''}, {'status': 'shipped'}, {}):
            with self.subTest(data=data):
                response = self.staff_post('dashboard_delivery_status', [self.booking.id], **data)
                self.assertEqual(response.status_code, 302)
                self.assertFlashLevel(response, flash_levels.ERROR)
                self.assertEqual(self.state(), ('pending', 'pending'))

    def test_same_status_changes_nothing_not_even_the_order(self):
        DeliveryBooking.objects.filter(pk=self.booking.pk).update(status='in_transit')
        response = self.set_status('in_transit')

        self.assertFlashLevel(response, flash_levels.INFO)
        self.assertEqual(self.state(), ('in_transit', 'pending'))

    def test_a_booking_without_an_order(self):
        standalone = self.make_booking(order=None)
        for status in ('in_transit', 'delivered'):
            response = self.set_status(status, standalone)
            self.assertFlashLevel(response, flash_levels.SUCCESS)
            self.assertEqual(DeliveryBooking.objects.get(pk=standalone.pk).status, status)

    def test_only_the_linked_order_follows(self):
        bystander = self.make_order()
        self.set_status('delivered')
        self.assertEqual(Order.objects.get(pk=bystander.pk).status, 'pending')

    def test_delivered_money_moves_to_the_delivered_figures(self):
        self.set_status('delivered')
        kpis = self.overview()['kpis']
        self.assertMoney(kpis['delivery_revenue_delivered'], '5.00')
        self.assertMoney(kpis['goods_revenue_delivered'], '20.00')
        self.assertMoney(kpis['total_revenue'], '25.00')


class RebookingTests(DashboardContractCase):
    def setUp(self):
        self.order = self.make_order('20.00')
        self.booking = self.make_booking('5.00', order=self.order)
        self.form = {
            'delivery_date': (date.today() + timedelta(days=2)).isoformat(), 'time_slot': 'afternoon',
            'delivery_address': '12 Samora Machel Ave', 'delivery_city': 'Harare',
            'delivery_phone': '0771234567', 'special_instructions': '',
        }

    def test_a_live_booking_blocks_a_second_one(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('delivery_booking'), self.form)

        self.assertRedirects(response, reverse('delivery_bookings'), fetch_redirect_response=False)
        self.assertEqual(DeliveryBooking.objects.count(), 1)

    def test_the_customer_can_book_again_after_staff_cancel_the_delivery(self):
        self.staff_post('dashboard_delivery_status', [self.booking.id], status='cancelled')
        self.assertEqual(Order.objects.get(pk=self.order.pk).status, 'pending')

        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('delivery_booking')).status_code, 200)
        response = self.client.post(reverse('delivery_booking'), self.form)

        self.assertRedirects(response, reverse('delivery_bookings'), fetch_redirect_response=False)
        new = DeliveryBooking.objects.exclude(pk=self.booking.pk).get()
        self.assertEqual((new.order, new.status, new.delivery_fee), (self.order, 'pending', Decimal('5.00')))

        # The replacement is the only fee owed, and it can't be doubled up again.
        self.client.post(reverse('delivery_booking'), self.form)
        self.assertEqual(DeliveryBooking.objects.count(), 2)
        self.assertMoney(self.overview()['kpis']['delivery_revenue'], '5.00')
        detail = self.staff_get('dashboard_order_detail', [self.order.id]).context
        self.assertEqual(detail['delivery'], new)


class DeliveriesPageTests(FrozenClockCase):
    def setUp(self):
        super().setUp()
        self.order = self.make_order()
        self.yesterday = self.make_booking(delivery_date=TODAY - timedelta(days=1), status='delivered',
                                           delivery_address='4 Yesterday Close')
        self.today = self.make_booking(delivery_date=TODAY, status='in_transit', order=self.order,
                                       delivery_address='5 Today Drive')
        self.tomorrow = self.make_booking(delivery_date=TODAY + timedelta(days=1), delivery_address='6 Tomorrow Way')

    def ids(self, **params):
        return {b.id for b in self.staff_get('dashboard_deliveries', **params).context['bookings']}

    def test_counts_and_status_filter(self):
        context = self.staff_get('dashboard_deliveries').context
        self.assertEqual((context['active_status'], context['active_when'], context['today']), ('all', 'all', TODAY))
        self.assertEqual(context['counts'], {'all': 3, 'pending': 1, 'confirmed': 0, 'in_transit': 1,
                                             'delivered': 1, 'cancelled': 0})
        self.assertEqual(list(context['status_choices']), list(DeliveryBooking.STATUS_CHOICES))
        self.assertEqual(context['nav']['active'], 'deliveries')
        self.assertEqual(self.ids(status='in_transit'), {self.today.id})
        self.assertEqual(self.staff_get('dashboard_deliveries', status='bogus').context['active_status'], 'all')

    def test_when_filter_and_search(self):
        self.assertEqual(self.ids(when='today'), {self.today.id})
        self.assertNotIn(self.yesterday.id, self.ids(when='upcoming'))
        self.assertIn(self.tomorrow.id, self.ids(when='upcoming'))
        self.assertEqual(self.staff_get('dashboard_deliveries', when='bogus').context['active_when'], 'all')
        self.assertEqual(self.ids(search='tomorrow way'), {self.tomorrow.id})
        self.assertEqual(self.ids(search='tendai'), {self.yesterday.id, self.today.id, self.tomorrow.id})

    def test_today_is_the_local_date_just_after_midnight(self):
        with freeze(local_dt(TODAY, 0, 30)):
            context = self.staff_get('dashboard_deliveries', when='today').context
        self.assertEqual(context['today'], TODAY)
        self.assertEqual({b.id for b in context['bookings']}, {self.today.id})


class MessagesPageTests(DashboardContractCase):
    def test_counts_and_open_filter(self):
        ContactMessage.objects.create(name='A', subject='open one', message='m', message_type='complaint', is_urgent=True)
        ContactMessage.objects.create(name='B', subject='answered', message='m', status='replied', is_read=True)
        ContactMessage.objects.create(name='C', subject='closed', message='m', status='resolved', is_read=True)

        context = self.staff_get('dashboard_messages').context
        self.assertEqual(
            (context['total_messages'], context['unread_messages'], context['total_complaints'],
             context['urgent_count'], context['open_count']),
            (3, 1, 1, 1, 1),
        )
        self.assertEqual(context['nav']['active'], 'messages')
        self.assertEqual(context['nav']['open_messages'], 1)

        context = self.staff_get('dashboard_messages', filter='open').context
        self.assertEqual(context['active_filter'], 'open')
        self.assertEqual([m.subject for m in context['contact_messages']], ['open one'])


# ---------------------------------------------------------------------------
# Rules that live in the templates
# ---------------------------------------------------------------------------

class TemplateContractTests(FrozenClockCase):
    ORDER_CONFIRM = ('data-confirm="This cancels the order and returns its items to stock. '
                     'It can\'t be undone."')

    def test_orders_page_keeps_cancel_out_of_the_select_and_behind_a_confirm(self):
        order = self.make_order(status='pending')

        response = self.staff_get('dashboard_orders', status='pending')

        self.assertNotContains(response, '<option value="cancelled"')
        self.assertContains(response, '<option value="processing"')
        self.assertContains(response, '<input type="hidden" name="status" value="cancelled">', count=1)
        self.assertContains(response, self.ORDER_CONFIRM, count=1)
        # Both row forms return staff to the filtered list they were working in.
        self.assertContains(response, 'name="next" value="/founder/orders/?status=pending"', count=2)

        detail = self.staff_get('dashboard_order_detail', [order.id])
        self.assertContains(detail, self.ORDER_CONFIRM, count=1)
        self.assertNotContains(detail, '<option value="cancelled"')

    def test_deliveries_page_keeps_cancel_out_of_the_select_and_behind_a_confirm(self):
        self.make_booking(status='pending')

        response = self.staff_get('dashboard_deliveries', status='pending')

        self.assertNotContains(response, '<option value="cancelled"')
        self.assertContains(response, '<option value="in_transit"')
        self.assertContains(response, '<input type="hidden" name="status" value="cancelled">', count=1)
        self.assertContains(response, 'data-confirm="This cancels the delivery booking.', count=1)
        self.assertContains(response, 'name="next" value="/founder/deliveries/?status=pending"', count=2)

    def test_a_cancelled_row_offers_no_status_form(self):
        self.make_order(status='cancelled')
        self.make_booking(status='cancelled')

        for url_name in ('dashboard_orders', 'dashboard_deliveries'):
            response = self.staff_get(url_name)
            self.assertNotContains(response, 'name="status"')
            self.assertNotContains(response, 'data-confirm')

    def test_overview_renders_the_chart_numbers_as_a_table_without_javascript(self):
        self.make_order('12.50')
        self.make_booking('5.00')

        response = self.staff_get('founder_dashboard', range='7d')

        self.assertContains(response, 'data-chart-table', count=1)
        self.assertContains(response, '<caption class="sr-only">Revenue per day, last 7 days</caption>')
        self.assertContains(response, '>12 Mar</th>', count=1)
        self.assertContains(response, '>6 Mar</th>', count=1)
        self.assertContains(response, '$17.50')

    def test_overview_without_sales_shows_an_empty_state_instead_of_the_table(self):
        response = self.staff_get('founder_dashboard')

        self.assertNotContains(response, 'data-chart-table')
        self.assertNotContains(response, 'data-chart-toggle')
        self.assertContains(response, 'No sales in the last 30 days')

    def test_overview_status_counts_are_not_links(self):
        # They count the period only; the lists a link would open cover all time.
        self.make_order(status='delivered')
        self.make_booking(status='delivered')

        response = self.staff_get('founder_dashboard')

        self.assertNotContains(response, '?status=')

    def test_restock_buttons_land_on_the_restock_form(self):
        product = self.make_product('Nearly gone', stock=1)
        edit_url = reverse('dashboard_product_edit', args=[product.id])

        self.assertContains(self.staff_get('founder_dashboard'), f'href="{edit_url}#restock"', count=1)
        self.assertContains(self.staff_get('dashboard_product_edit', [product.id]), 'id="restock"', count=1)

    def test_stock_log_folds_its_hidden_columns_under_the_visible_cell(self):
        # Cost, supplier, note and "By" are columns only on wide screens, so
        # each fact is written twice: in its column and under the first cell.
        clerk = User.objects.create_user('qw', password='pw', is_staff=True, first_name='Qwertina')
        product = self.make_product('Maize', supplier='National Foods')
        StockEntry.objects.create(product=product, kind='restock', quantity=30, unit_cost=Decimal('4.37'),
                                  supplier='Zorkmid Wholesalers', note='Invoice ZX-991', stock_after=50,
                                  created_by=clerk)
        StockEntry.objects.create(product=product, kind='adjustment', quantity=-3, note='two bags split open',
                                  stock_after=47, created_by=clerk)

        for url_name, args in (('dashboard_stock_history', []), ('dashboard_product_edit', [product.id])):
            with self.subTest(page=url_name):
                response = self.staff_get(url_name, args)
                for fact in ('$4.37 each', 'Zorkmid Wholesalers', 'Invoice ZX-991', 'two bags split open'):
                    self.assertContains(response, fact, count=2)
                self.assertContains(response, 'By Qwertina', count=2)

    def test_nav_marks_only_the_active_section(self):
        hrefs = {
            'overview': '/founder/', 'inventory': '/founder/inventory/', 'orders': '/founder/orders/',
            'deliveries': '/founder/deliveries/', 'messages': '/founder/messages/',
        }
        for active, href in hrefs.items():
            with self.subTest(active=active):
                html = render_to_string('partials/dashboard_nav.html', {'nav': {'active': active}})
                self.assertEqual(html.count('aria-current="page"'), 1)
                self.assertEqual(html.count('is-active'), 1)
                self.assertIn(f'is-active" href="{href}" aria-current="page"', html)

    def test_nav_badges_show_only_what_is_waiting(self):
        quiet = {'active': 'overview', 'out_of_stock': 0, 'low_stock': 4, 'pending_orders': 0,
                 'pending_deliveries': 0, 'open_messages': 0}
        self.assertNotIn('tab-count', render_to_string('partials/dashboard_nav.html', {'nav': quiet}))

        busy = dict(quiet, out_of_stock=2, pending_orders=3, pending_deliveries=5, open_messages=7)
        html = render_to_string('partials/dashboard_nav.html', {'nav': busy})
        self.assertEqual(html.count('tab-count'), 4)
        for badge in ('>2<span class="sr-only"> out of stock</span>', '>3<span class="sr-only"> pending</span>',
                      '>5<span class="sr-only"> pending</span>', '>7<span class="sr-only"> awaiting a reply</span>'):
            self.assertIn(badge, html)

    def test_marking_a_message_unread_returns_to_the_messages_page(self):
        message = ContactMessage.objects.create(name='A', subject='s', message='m')

        response = self.staff_get('message_detail', [message.id])

        self.assertContains(response, 'data-post-redirect="/founder/messages/"', count=1)
