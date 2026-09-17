"""The numbers and stock operations behind the staff dashboard.

Nothing here knows about requests or templates, so every rule can be tested
directly. admin_views.py parses the input, calls these functions and renders.

How revenue is defined (the dashboard's help text says the same):

* Goods sales: Order.total_amount of orders that aren't cancelled, by the date
  the order was placed. Orders a customer cancels themselves are deleted, so
  they never count either.
* Delivery fees: DeliveryBooking.delivery_fee of bookings that aren't
  cancelled, by the date the booking was made.
* Customers pay cash or mobile money on delivery, so only the "delivered"
  part of each figure is money that has certainly been received.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Case, Count, DecimalField, F, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import ContactMessage, DeliveryBooking, Order, OrderItem, Product, StockEntry

CENT = Decimal('0.01')
MONEY_FIELD = DecimalField(max_digits=14, decimal_places=2)

RANGE_OPTIONS = [('7d', '7 days'), ('30d', '30 days'), ('90d', '90 days'), ('12m', '12 months')]
DEFAULT_RANGE = '30d'
RANGE_DAYS = {'7d': 7, '30d': 30, '90d': 90}
RANGE_BUCKETS = {'7d': 'day', '30d': 'day', '90d': 'week', '12m': 'month'}

# Which products each stock state covers. Mirrors Product.stock_state so the
# database filters and the badge on each row can never disagree.
STOCK_STATE_FILTERS = {
    'in': Q(is_available=True, stock_quantity__gt=Product.LOW_STOCK_THRESHOLD),
    'low': Q(is_available=True, stock_quantity__gte=1, stock_quantity__lte=Product.LOW_STOCK_THRESHOLD),
    'out': Q(is_available=True, stock_quantity=0),
    'hidden': Q(is_available=False),
}

# Deliveries that still need doing.
ACTIVE_DELIVERY_STATUSES = ['pending', 'confirmed', 'in_transit']


def money(value):
    """A Decimal with exactly two places; None (an empty Sum) counts as zero."""
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


# Periods ---------------------------------------------------------------------

@dataclass(frozen=True)
class Period:
    """A reporting period in local calendar days, both ends included."""
    key: str
    label: str
    previous_label: str
    start: date
    end: date
    previous_start: date
    previous_end: date
    bucket: str  # 'day', 'week' or 'month'


def month_start(day, months_back=0):
    """The first day of the month `months_back` months before `day`'s month."""
    index = day.year * 12 + (day.month - 1) - months_back
    return date(index // 12, index % 12 + 1, 1)


def get_period(range_key=None, today=None):
    """The period for a ?range= value; anything unknown means the default.

    `today` is the local date, passed in only by tests.
    """
    key = range_key if range_key in RANGE_BUCKETS else DEFAULT_RANGE
    today = today or timezone.localdate()
    words = dict(RANGE_OPTIONS)[key]

    if key == '12m':
        start = month_start(today, 11)
        previous_start = month_start(today, 23)
    else:
        days = RANGE_DAYS[key]
        start = today - timedelta(days=days - 1)
        previous_start = start - timedelta(days=days)

    return Period(
        key=key,
        label=f'Last {words}',
        previous_label=f'previous {words}',
        start=start,
        end=today,
        previous_start=previous_start,
        previous_end=start - timedelta(days=1),
        bucket=RANGE_BUCKETS[key],
    )


def day_window(start, end):
    """Aware datetimes [start 00:00, end + 1 day 00:00) in local time.

    Filtering on these instead of created_at__date keeps the day boundaries in
    Africa/Harare on every database.
    """
    tz = timezone.get_current_timezone()
    begin = timezone.make_aware(datetime.combine(start, time.min), tz)
    finish = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
    return begin, finish


def created_between(queryset, start, end, field='created_at'):
    begin, finish = day_window(start, end)
    return queryset.filter(**{f'{field}__gte': begin, f'{field}__lt': finish})


def bucket_start(day, bucket):
    """The first day of the bucket that `day` falls in (weeks start on Monday)."""
    if bucket == 'week':
        return day - timedelta(days=day.weekday())
    if bucket == 'month':
        return day.replace(day=1)
    return day


def bucket_starts(period):
    """Every bucket of the period in order, including ones with no sales."""
    current = bucket_start(period.start, period.bucket)
    starts = []
    while current <= period.end:
        starts.append(current)
        if period.bucket == 'month':
            current = month_start(current, -1)
        else:
            current += timedelta(days=7 if period.bucket == 'week' else 1)
    return starts


def bucket_label(day, bucket):
    return f'{day:%b %Y}' if bucket == 'month' else f'{day.day} {day:%b}'


# Revenue ---------------------------------------------------------------------

def sales_totals(start, end):
    """Goods and delivery money booked between two local days, cancelled excluded."""
    orders = created_between(Order.objects.exclude(status='cancelled'), start, end).aggregate(
        total=Sum('total_amount'),
        delivered=Sum('total_amount', filter=Q(status='delivered')),
        count=Count('id'),
    )
    bookings = created_between(DeliveryBooking.objects.exclude(status='cancelled'), start, end).aggregate(
        total=Sum('delivery_fee'),
        delivered=Sum('delivery_fee', filter=Q(status='delivered')),
        count=Count('id'),
    )
    return {
        'goods_revenue': money(orders['total']),
        'goods_revenue_delivered': money(orders['delivered']),
        'delivery_revenue': money(bookings['total']),
        'delivery_revenue_delivered': money(bookings['delivered']),
        'total_revenue': money(orders['total']) + money(bookings['total']),
        'orders_count': orders['count'],
        'deliveries_booked': bookings['count'],
    }


def stock_bought(start, end):
    """Units received from suppliers, and what they cost where a cost was recorded."""
    totals = created_between(StockEntry.objects.filter(kind='restock'), start, end).aggregate(
        units=Sum('quantity'),
        cost=Sum(F('quantity') * F('unit_cost'), output_field=MONEY_FIELD),
    )
    return {'units': totals['units'] or 0, 'cost': money(totals['cost'])}


def period_kpis(period):
    """The headline figures for the overview page."""
    kpis = sales_totals(period.start, period.end)
    previous_total = sales_totals(period.previous_start, period.previous_end)['total_revenue']

    # A percentage of nothing is meaningless, so the page says "no sales in
    # the previous period" instead.
    change = None
    if previous_total:
        change = ((kpis['total_revenue'] - previous_total) / previous_total * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        )

    units_sold = created_between(
        OrderItem.objects.exclude(order__status='cancelled'), period.start, period.end, 'order__created_at'
    ).aggregate(units=Sum('quantity'))['units'] or 0

    average = Decimal('0.00')
    if kpis['orders_count']:
        average = money(kpis['goods_revenue'] / kpis['orders_count'])

    bought = stock_bought(period.start, period.end)
    kpis.update({
        'prev_total_revenue': previous_total,
        'revenue_change_pct': change,
        'units_sold': units_sold,
        'average_order_value': average,
        'stock_bought_units': bought['units'],
        'stock_bought_cost': bought['cost'],
    })
    return kpis


def revenue_chart(period):
    """Revenue per bucket, zero-filled, as JSON-ready floats for the chart.

    Rows are bucketed here rather than with database date functions: the
    volumes are small, and SQLite and Postgres disagree about time zones.
    """
    buckets = {
        start: {'goods': Decimal(0), 'delivery': Decimal(0), 'orders': 0}
        for start in bucket_starts(period)
    }

    def bucket_for(created_at):
        return buckets[bucket_start(timezone.localtime(created_at).date(), period.bucket)]

    orders = created_between(Order.objects.exclude(status='cancelled'), period.start, period.end)
    for created_at, amount in orders.values_list('created_at', 'total_amount'):
        bucket = bucket_for(created_at)
        bucket['goods'] += amount
        bucket['orders'] += 1

    bookings = created_between(DeliveryBooking.objects.exclude(status='cancelled'), period.start, period.end)
    has_bookings = False
    for created_at, fee in bookings.values_list('created_at', 'delivery_fee'):
        bucket_for(created_at)['delivery'] += fee
        has_bookings = True

    points = [
        {
            'label': bucket_label(start, period.bucket),
            'start': start.isoformat(),
            'goods': round(float(values['goods']), 2),
            'delivery': round(float(values['delivery']), 2),
            'total': round(float(values['goods'] + values['delivery']), 2),
            'orders': values['orders'],
        }
        for start, values in buckets.items()
    ]
    has_data = has_bookings or any(point['orders'] for point in points)
    return {'bucket': period.bucket, 'points': points, 'has_data': has_data}


def top_products(period, limit=8):
    """Best sellers by revenue in the period.

    share_pct is each product's revenue against the best seller's, which is
    what sizes the bars on the overview page.
    """
    items = created_between(
        OrderItem.objects.exclude(order__status='cancelled'), period.start, period.end, 'order__created_at'
    )
    rows = list(
        items.values('product_id', 'product__name')
        .annotate(units=Sum('quantity'), revenue=Sum(F('quantity') * F('price'), output_field=MONEY_FIELD))
        .order_by('-revenue', 'product__name')[:limit]
    )
    best = money(rows[0]['revenue']) if rows else Decimal(0)
    return [
        {
            'product_id': row['product_id'],
            'name': row['product__name'],
            'units': row['units'],
            'revenue': money(row['revenue']),
            'share_pct': int((money(row['revenue']) * 100 / best).to_integral_value(ROUND_HALF_UP)) if best else 0,
        }
        for row in rows
    ]


def status_breakdown(model, period):
    """How many of the period's orders or bookings are in each status, zeros included."""
    counts = dict(
        created_between(model.objects.all(), period.start, period.end)
        .order_by().values_list('status').annotate(count=Count('id'))
    )
    return [
        {'status': status, 'label': label, 'count': counts.get(status, 0)}
        for status, label in model.STATUS_CHOICES
    ]


# Stock levels ----------------------------------------------------------------

def state_counts(products):
    """Count a product queryset by stock state: all, in, low, out and hidden."""
    return products.aggregate(
        all=Count('id'),
        **{state: Count('id', filter=condition) for state, condition in STOCK_STATE_FILTERS.items()},
    )


def inventory_summary():
    """Stock state counts for the whole catalogue, plus what the shelves are worth."""
    counts = state_counts(Product.objects.all())
    retail_value = Product.objects.filter(is_available=True).aggregate(
        value=Sum(F('stock_quantity') * F('price'), output_field=MONEY_FIELD)
    )['value']
    return {
        'total': counts['all'],
        'in_stock': counts['in'],
        'low_stock': counts['low'],
        'out_of_stock': counts['out'],
        'hidden': counts['hidden'],
        'retail_value': money(retail_value),
    }


def with_units_sold(products):
    """Annotate products with all-time units sold on orders that weren't cancelled."""
    return products.annotate(
        units_sold=Coalesce(
            Sum('orderitem__quantity', filter=~Q(orderitem__order__status='cancelled')), Value(0)
        )
    )


def stock_alerts(limit=8):
    """Products customers can see that are out of stock or about to be."""
    return (
        Product.objects.filter(STOCK_STATE_FILTERS['out'] | STOCK_STATE_FILTERS['low'])
        .select_related('category')
        .order_by('stock_quantity', 'name')[:limit]
    )


def in_delivery_order(bookings, descending=False):
    """Order bookings by delivery date, then by time of day.

    The time slots are stored as words, which sort alphabetically with the
    afternoon before the morning.
    """
    slot_position = Case(
        *[When(time_slot=slot, then=Value(position))
          for position, (slot, _label) in enumerate(DeliveryBooking.TIME_SLOT_CHOICES)],
        default=Value(len(DeliveryBooking.TIME_SLOT_CHOICES)),
        output_field=IntegerField(),
    )
    date_field = '-delivery_date' if descending else 'delivery_date'
    return bookings.annotate(slot_position=slot_position).order_by(date_field, 'slot_position', 'id')


def upcoming_deliveries(limit=6, today=None):
    today = today or timezone.localdate()
    bookings = DeliveryBooking.objects.filter(
        delivery_date__gte=today, status__in=ACTIVE_DELIVERY_STATUSES
    ).select_related('user', 'order')
    return in_delivery_order(bookings)[:limit]


def nav_counts(active):
    """The `nav` dict every dashboard page needs for its tabs and their badges."""
    stock = Product.objects.aggregate(
        out=Count('id', filter=STOCK_STATE_FILTERS['out']),
        low=Count('id', filter=STOCK_STATE_FILTERS['low']),
    )
    return {
        'active': active,
        'out_of_stock': stock['out'],
        'low_stock': stock['low'],
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_deliveries': DeliveryBooking.objects.filter(status='pending').count(),
        'open_messages': ContactMessage.objects.filter(status='open').count(),
    }


# Stock changes ---------------------------------------------------------------
# Every change staff make is atomic and leaves a StockEntry behind, so the
# history page can always explain how a product reached its current level.

@transaction.atomic
def restock_product(product, quantity, *, unit_cost=None, supplier='', note='', user=None):
    """Add stock received from a supplier and log it. Returns the StockEntry."""
    # F() rather than read-modify-write: a customer may be checking out the
    # same product at this moment.
    Product.objects.filter(pk=product.pk).update(
        stock_quantity=F('stock_quantity') + quantity, updated_at=timezone.now()
    )
    product.refresh_from_db(fields=['stock_quantity'])
    return StockEntry.objects.create(
        product=product, kind='restock', quantity=quantity, unit_cost=unit_cost,
        supplier=supplier or product.supplier, note=note,
        stock_after=product.stock_quantity, created_by=user,
    )


@transaction.atomic
def adjust_stock(product_id, new_quantity, *, note='', user=None):
    """Set a product's stock to a counted figure and log the difference.

    Returns the StockEntry, or None when the count matches what we already had.
    """
    product = Product.objects.select_for_update().get(pk=product_id)
    delta = new_quantity - product.stock_quantity
    if delta == 0:
        return None

    product.stock_quantity = new_quantity
    product.save(update_fields=['stock_quantity', 'updated_at'])
    return StockEntry.objects.create(
        product=product, kind='adjustment', quantity=delta, note=note,
        stock_after=new_quantity, created_by=user,
    )


# Order and delivery status ---------------------------------------------------
# The change_* functions return (level, message): the django.contrib.messages
# level to report with ('success', 'info' or 'error') and the text to show.

@dataclass(frozen=True)
class CancelResult:
    """What cancelling an order did to its delivery bookings.

    An instance is always truthy, so callers can still treat cancel_order's
    return value as "did it cancel".
    """
    bookings_cancelled: int
    delivered_kept: bool


@transaction.atomic
def cancel_order(order):
    """Cancel an order, return its items to stock and cancel its open deliveries.

    Returns False when the order was already cancelled, otherwise a
    CancelResult. The guarded UPDATE is what makes that safe: of two
    simultaneous requests only one can flip the status, so the stock can never
    be returned twice.
    """
    flipped = Order.objects.filter(pk=order.pk).exclude(status='cancelled').update(
        status='cancelled', updated_at=timezone.now()
    )
    if not flipped:
        return False

    for item in order.items.all():
        Product.objects.filter(pk=item.product_id).update(
            stock_quantity=F('stock_quantity') + item.quantity
        )

    # A completed delivery stays delivered: it happened, and its fee was earned.
    bookings = DeliveryBooking.objects.filter(order=order)
    open_bookings = list(bookings.exclude(status__in=['delivered', 'cancelled']))
    for booking in open_bookings:
        booking.cancel_delivery('other', 'Order cancelled by staff')

    order.status = 'cancelled'
    return CancelResult(
        bookings_cancelled=len(open_bookings),
        delivered_kept=bookings.filter(status='delivered').exists(),
    )


def change_order_status(order, new_status):
    """Apply a status chosen by staff to an order."""
    labels = dict(Order.STATUS_CHOICES)
    if new_status not in labels:
        return 'error', 'That is not a valid order status.'
    if new_status == order.status:
        return 'info', f'Order #{order.order_number} is already {labels[new_status].lower()}.'

    final = (f'Order #{order.order_number} is cancelled and its items are back in stock, '
             'so its status can no longer be changed.')
    if order.status == 'cancelled':
        return 'error', final

    if new_status == 'cancelled':
        result = cancel_order(order)
        if not result:
            return 'error', final
        # Say only what happened to the delivery: a delivered booking is left
        # alone and an order may have no booking at all.
        message = f'Order #{order.order_number} cancelled. Its items were returned to stock.'
        if result.bookings_cancelled:
            message += ' Its delivery booking was cancelled too.'
        if result.delivered_kept:
            message += ' Its delivery was already completed, so that booking stays delivered and its fee still counts.'
        return 'success', message

    # Staff may move an order in either direction to fix a mistake. The guard
    # only stops this overwriting a cancellation made a moment ago elsewhere.
    moved = Order.objects.filter(pk=order.pk).exclude(status='cancelled').update(
        status=new_status, updated_at=timezone.now()
    )
    if not moved:
        return 'error', final
    order.status = new_status
    return 'success', f'Order #{order.order_number} marked as {labels[new_status].lower()}.'


def sync_order_with_delivery(booking):
    """Keep the linked order in step with its delivery. Returns the order's new status or None.

    Only ever moves an order forward: out for delivery means shipped, and a
    completed delivery means delivered. A cancelled order is never touched.
    """
    if not booking.order_id:
        return None
    if booking.status == 'in_transit':
        new_status, movable = 'shipped', Q(status__in=['pending', 'processing'])
    elif booking.status == 'delivered':
        new_status, movable = 'delivered', ~Q(status__in=['cancelled', 'delivered'])
    else:
        return None

    moved = Order.objects.filter(movable, pk=booking.order_id).update(
        status=new_status, updated_at=timezone.now()
    )
    return new_status if moved else None


@transaction.atomic
def change_delivery_status(booking_id, new_status):
    """Apply a status chosen by staff to a delivery booking."""
    # Locked so two staff updating the same booking can't interleave.
    booking = DeliveryBooking.objects.select_for_update().get(pk=booking_id)
    labels = dict(DeliveryBooking.STATUS_CHOICES)
    if new_status not in labels:
        return 'error', 'That is not a valid delivery status.'
    if new_status == booking.status:
        return 'info', f'Delivery #{booking.id} is already {labels[new_status].lower()}.'
    if booking.status == 'cancelled':
        return 'error', f'Delivery #{booking.id} is cancelled and can no longer be changed.'

    if new_status == 'cancelled':
        booking.cancel_delivery('other', 'Cancelled by staff')
        return 'success', f'Delivery #{booking.id} cancelled.'

    booking.status = new_status
    booking.save(update_fields=['status', 'updated_at'])
    message = f'Delivery #{booking.id} marked as {labels[new_status].lower()}.'

    order_status = sync_order_with_delivery(booking)
    if order_status:
        order_label = dict(Order.STATUS_CHOICES)[order_status].lower()
        message += f' Order #{booking.order.order_number} is now {order_label} as well.'
    return 'success', message
