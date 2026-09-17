from django.contrib import messages as flash
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import dashboard
from .forms import ProductForm, RestockForm, StaffReplyForm, StockAdjustForm
from .models import Category, ContactMessage, DeliveryBooking, Order, Product, StockEntry
from .views import parse_id


# Quick filters offered on the messages page's tabs.
MESSAGE_FILTERS = {
    'open': Q(status='open'),
    'unread': Q(is_read=False),
    'complaints': Q(message_type='complaint'),
    'urgent': Q(is_urgent=True),
}

INVENTORY_SORTS = {
    'name': ['name'],
    'stock_low': ['stock_quantity', 'name'],
    'stock_high': ['-stock_quantity', 'name'],
    'newest': ['-created_at'],
}


def is_founder(user):
    """Check if the user is allowed into the founder dashboard.

    This used to compare the profile's phone number against a hardcoded
    value. That number is printed on the public contact and delivery pages,
    and any registered user could type it into their own profile to grant
    themselves access to every customer's messages, orders and addresses.
    Staff status is set by a superuser and cannot be self-assigned.
    """
    return user.is_authenticated and user.is_staff


def _page(request, queryset, per_page):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def _redirect_back(request, fallback):
    """Return to the page the form was posted from, or to `fallback`.

    `next` arrives from the browser, so it is only followed when it points
    back at this site.
    """
    target = request.POST.get('next', '')
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return HttpResponseRedirect(target)
    return redirect(fallback)


def _report(request, outcome):
    """Show a (level, message) result from dashboard.py as a toast."""
    level, message = outcome
    getattr(flash, level)(request, message)


def _first_error(form):
    """One readable sentence from an invalid small form, for an error toast."""
    field, errors = next(iter(form.errors.items()))
    label = form.fields[field].label or field.replace('_', ' ').capitalize()
    return f'{label}: {errors[0]}'


def _status_counts(queryset, choices):
    """{'all': n, '<status>': n, ...} with every status present, even at zero."""
    counts = dict(queryset.order_by().values_list('status').annotate(count=Count('id')))
    result = {'all': sum(counts.values())}
    result.update({status: counts.get(status, 0) for status, _label in choices})
    return result


# Overview --------------------------------------------------------------------

@user_passes_test(is_founder)
def founder_dashboard(request):
    """Sales, stock and deliveries at a glance for the chosen period."""
    period = dashboard.get_period(request.GET.get('range'))

    context = {
        'nav': dashboard.nav_counts('overview'),
        'range_key': period.key,
        'range_label': period.label,
        'range_options': dashboard.RANGE_OPTIONS,
        'period_start': period.start,
        'period_end': period.end,
        'previous_label': period.previous_label,
        'kpis': dashboard.period_kpis(period),
        'chart': dashboard.revenue_chart(period),
        'top_products': dashboard.top_products(period),
        'orders_by_status': dashboard.status_breakdown(Order, period),
        'deliveries_by_status': dashboard.status_breakdown(DeliveryBooking, period),
        'inventory': dashboard.inventory_summary(),
        'stock_alerts': dashboard.stock_alerts(),
        'upcoming_deliveries': dashboard.upcoming_deliveries(),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:6],
        'awaiting_messages': ContactMessage.objects.filter(status='open').order_by('-created_at')[:4],
    }
    return render(request, 'supermarket/dashboard/overview.html', context)


# Inventory -------------------------------------------------------------------

@user_passes_test(is_founder)
def inventory(request):
    """Every product with its stock level, including ones hidden from the shop."""
    products = Product.objects.all()

    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(supplier__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # A ?category= that isn't a usable id is ignored instead of raising.
    category_id = parse_id(request.GET.get('category'))
    if category_id:
        products = products.filter(category_id=category_id)
    # A string, because the template compares it with category.id|stringformat.
    selected_category = str(category_id) if category_id else ''

    # Counted before the stock filter, so each tab shows how many products
    # clicking it will list for the current search.
    counts = dashboard.state_counts(products)

    active_filter = request.GET.get('filter', 'all')
    if active_filter in dashboard.STOCK_STATE_FILTERS:
        products = products.filter(dashboard.STOCK_STATE_FILTERS[active_filter])
    else:
        active_filter = 'all'

    sort = request.GET.get('sort')
    if sort not in INVENTORY_SORTS:
        sort = 'stock_low'
    products = dashboard.with_units_sold(products.select_related('category')).order_by(*INVENTORY_SORTS[sort])

    context = {
        'nav': dashboard.nav_counts('inventory'),
        'products': _page(request, products, 24),
        'active_filter': active_filter,
        'counts': counts,
        'search_query': search_query,
        'categories': Category.objects.all(),
        'selected_category': selected_category,
        'sort': sort,
        'inventory': dashboard.inventory_summary(),
    }
    return render(request, 'supermarket/dashboard/inventory.html', context)


@user_passes_test(is_founder)
def product_add(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            product = form.save()
            opening_stock = form.cleaned_data.get('opening_stock') or 0
            if opening_stock:
                dashboard.restock_product(product, opening_stock, note='Opening stock', user=request.user)
        flash.success(request, f'{product.name} added.')
        return redirect('dashboard_inventory')

    context = {
        'nav': dashboard.nav_counts('inventory'),
        'form': form,
        'product': None,
    }
    return render(request, 'supermarket/dashboard/product_form.html', context)


@user_passes_test(is_founder)
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        # Only the form's own columns. A full save would also write back the
        # stock level read at the start of this request, undoing any sale or
        # restock that landed in between without leaving a trace.
        form.save(commit=False).save(update_fields=[*ProductForm.Meta.fields, 'updated_at'])
        flash.success(request, f'{product.name} saved.')
        return redirect('dashboard_product_edit', product_id=product.id)

    context = {
        'nav': dashboard.nav_counts('inventory'),
        'form': form,
        'product': product,
        'restock_form': RestockForm(initial={'supplier': product.supplier}),
        'adjust_form': StockAdjustForm(initial={'new_quantity': product.stock_quantity}),
        'entries': product.stock_entries.select_related('created_by').order_by('-created_at', '-id')[:10],
    }
    return render(request, 'supermarket/dashboard/product_form.html', context)


@user_passes_test(is_founder)
@require_POST
def restock(request, product_id):
    """Record stock received from a supplier."""
    product = get_object_or_404(Product, id=product_id)
    form = RestockForm(request.POST)
    if form.is_valid():
        entry = dashboard.restock_product(product, user=request.user, **form.cleaned_data)
        flash.success(request, f'Added {entry.quantity} to {product.name}. Stock is now {entry.stock_after}.')
    else:
        flash.error(request, f"{product.name} wasn't restocked. {_first_error(form)}")
    return _redirect_back(request, 'dashboard_inventory')


@user_passes_test(is_founder)
@require_POST
def adjust_stock(request, product_id):
    """Correct a product's stock level after a count."""
    product = get_object_or_404(Product, id=product_id)
    form = StockAdjustForm(request.POST)
    if not form.is_valid():
        flash.error(request, f"{product.name} wasn't changed. {_first_error(form)}")
        return _redirect_back(request, 'dashboard_inventory')

    entry = dashboard.adjust_stock(
        product.id, form.cleaned_data['new_quantity'], note=form.cleaned_data['note'], user=request.user
    )
    if entry is None:
        flash.info(request, f"{product.name} already has {form.cleaned_data['new_quantity']} in stock, so nothing changed.")
    else:
        flash.success(request, f'{product.name} corrected by {entry.quantity:+d}. Stock is now {entry.stock_after}.')
    return _redirect_back(request, 'dashboard_inventory')


@user_passes_test(is_founder)
@require_POST
def toggle_available(request, product_id):
    """Hide a product from the shop, or show it again."""
    product = get_object_or_404(Product, id=product_id)
    product.is_available = not product.is_available
    product.save(update_fields=['is_available', 'updated_at'])

    # The page reloads after this call and the row may have left the current
    # stock tab, so the toast is the only thing that says what just happened.
    if product.is_available:
        flash.success(request, f'{product.name} is showing in the shop again.')
    else:
        flash.success(request, f'{product.name} is now hidden from the shop. Find it under the Hidden tab to show it again.')
    return JsonResponse({'success': True, 'is_available': product.is_available})


@user_passes_test(is_founder)
def stock_history(request):
    """The log of stock received and corrections, optionally for one product."""
    entries = StockEntry.objects.all()

    product_id = parse_id(request.GET.get('product'))
    product = Product.objects.filter(id=product_id).first() if product_id else None
    if product:
        entries = entries.filter(product=product)

    counts = entries.aggregate(
        all=Count('id'),
        restock=Count('id', filter=Q(kind='restock')),
        adjustment=Count('id', filter=Q(kind='adjustment')),
    )

    active_kind = request.GET.get('kind', 'all')
    if active_kind in dict(StockEntry.KIND_CHOICES):
        entries = entries.filter(kind=active_kind)
    else:
        active_kind = 'all'

    totals = entries.filter(kind='restock').aggregate(
        units_in=Sum('quantity'),
        cost=Sum(F('quantity') * F('unit_cost'), output_field=dashboard.MONEY_FIELD),
    )

    entries = entries.select_related('product', 'created_by').order_by('-created_at', '-id')
    context = {
        'nav': dashboard.nav_counts('inventory'),
        'entries': _page(request, entries, 30),
        'product': product,
        'active_kind': active_kind,
        'counts': counts,
        'totals': {'units_in': totals['units_in'] or 0, 'cost': dashboard.money(totals['cost'])},
    }
    return render(request, 'supermarket/dashboard/stock_history.html', context)


# Orders ----------------------------------------------------------------------

@user_passes_test(is_founder)
def orders(request):
    order_list = Order.objects.all()

    search_query = request.GET.get('search', '').strip()
    if search_query:
        order_list = order_list.filter(
            # Staff copy order numbers from pages that show them as "#ABC123".
            Q(order_number__icontains=search_query.lstrip('#')) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(delivery_phone__icontains=search_query) |
            Q(delivery_city__icontains=search_query)
        )

    counts = _status_counts(order_list, Order.STATUS_CHOICES)

    active_status = request.GET.get('status', 'all')
    if active_status in dict(Order.STATUS_CHOICES):
        order_list = order_list.filter(status=active_status)
    else:
        active_status = 'all'

    order_list = (
        order_list.select_related('user')
        .annotate(item_count=Coalesce(Sum('items__quantity'), 0))
        .order_by('-created_at')
    )
    context = {
        'nav': dashboard.nav_counts('orders'),
        'orders': _page(request, order_list, 20),
        'active_status': active_status,
        'counts': counts,
        'search_query': search_query,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'supermarket/dashboard/orders.html', context)


@user_passes_test(is_founder)
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related('user'), id=order_id)

    context = {
        'nav': dashboard.nav_counts('orders'),
        'order': order,
        'items': order.items.select_related('product'),
        'delivery': DeliveryBooking.objects.filter(order=order).order_by('-created_at', '-id').first(),
        'status_choices': Order.STATUS_CHOICES,
        'can_change_status': order.status != 'cancelled',
    }
    return render(request, 'supermarket/dashboard/order_detail.html', context)


@user_passes_test(is_founder)
@require_POST
def order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    _report(request, dashboard.change_order_status(order, request.POST.get('status', '')))
    return _redirect_back(request, 'dashboard_orders')


# Deliveries ------------------------------------------------------------------

@user_passes_test(is_founder)
def deliveries(request):
    today = timezone.localdate()
    bookings = DeliveryBooking.objects.all()

    search_query = request.GET.get('search', '').strip()
    if search_query:
        bookings = bookings.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(delivery_phone__icontains=search_query) |
            Q(delivery_city__icontains=search_query) |
            Q(delivery_address__icontains=search_query)
        )

    active_when = request.GET.get('when', 'all')
    if active_when == 'today':
        bookings = bookings.filter(delivery_date=today)
    elif active_when == 'upcoming':
        bookings = bookings.filter(delivery_date__gte=today)
    else:
        active_when = 'all'

    counts = _status_counts(bookings, DeliveryBooking.STATUS_CHOICES)

    active_status = request.GET.get('status', 'all')
    if active_status in dict(DeliveryBooking.STATUS_CHOICES):
        bookings = bookings.filter(status=active_status)
    else:
        active_status = 'all'

    # What's coming reads soonest first; the full list reads latest first.
    bookings = dashboard.in_delivery_order(
        bookings.select_related('user', 'order'), descending=active_when == 'all'
    )
    context = {
        'nav': dashboard.nav_counts('deliveries'),
        'bookings': _page(request, bookings, 20),
        'active_status': active_status,
        'counts': counts,
        'active_when': active_when,
        'search_query': search_query,
        'status_choices': DeliveryBooking.STATUS_CHOICES,
        'today': today,
    }
    return render(request, 'supermarket/dashboard/deliveries.html', context)


@user_passes_test(is_founder)
@require_POST
def delivery_status(request, booking_id):
    booking = get_object_or_404(DeliveryBooking, id=booking_id)
    _report(request, dashboard.change_delivery_status(booking.id, request.POST.get('status', '')))
    return _redirect_back(request, 'dashboard_deliveries')


# Messages --------------------------------------------------------------------

@user_passes_test(is_founder)
def dashboard_messages(request):
    """Customer messages and complaints, with quick filters."""
    messages = ContactMessage.objects.all().order_by('-created_at')

    # Apply the selected quick filter to the message list
    active_filter = request.GET.get('filter', 'all')
    if active_filter in MESSAGE_FILTERS:
        filtered_messages = messages.filter(MESSAGE_FILTERS[active_filter])
    else:
        active_filter = 'all'
        filtered_messages = messages
    filtered_messages = filtered_messages.annotate(reply_count=Count('replies'))

    context = {
        'nav': dashboard.nav_counts('messages'),
        # Not called `messages`: that name is Django's flash messages, which
        # base.html renders as toasts.
        'contact_messages': _page(request, filtered_messages, 20),
        'active_filter': active_filter,
        'total_messages': messages.count(),
        'unread_messages': messages.filter(is_read=False).count(),
        'total_complaints': messages.filter(message_type='complaint').count(),
        'urgent_count': messages.filter(is_urgent=True).count(),
        'open_count': messages.filter(status='open').count(),
    }
    return render(request, 'supermarket/dashboard/messages.html', context)


def _render_message_detail(request, message, reply_form=None):
    context = {
        'message': message,
        'replies': message.replies.select_related('author'),
        'reply_form': reply_form or StaffReplyForm(),
    }
    return render(request, 'supermarket/message_detail.html', context)


@user_passes_test(is_founder)
def message_detail(request, message_id):
    """Detailed view of a specific message and the conversation about it"""
    message = get_object_or_404(ContactMessage.objects.select_related('user'), id=message_id)

    # Mark as read when viewed
    if not message.is_read:
        message.is_read = True
        message.save(update_fields=['is_read'])

    return _render_message_detail(request, message)


@user_passes_test(is_founder)
@require_POST
def reply_to_message(request, message_id):
    """Add a staff reply to a customer's message."""
    message = get_object_or_404(ContactMessage.objects.select_related('user'), id=message_id)
    form = StaffReplyForm(request.POST)
    if not form.is_valid():
        return _render_message_detail(request, message, form)

    reply = form.save(commit=False)
    reply.message = message
    reply.author = request.user
    reply.from_staff = True
    reply.save()

    message.status = 'resolved' if form.cleaned_data['mark_resolved'] else 'replied'
    message.is_read = True
    message.save(update_fields=['status', 'is_read'])

    if message.user_id:
        flash.success(request, 'Reply sent. The customer will see it under My messages.')
    else:
        flash.success(
            request,
            'Reply saved. This customer wrote without an account, so send it using the WhatsApp or SMS button.'
        )
    return redirect(f"{reverse('message_detail', args=[message.id])}#reply-{reply.id}")


@user_passes_test(is_founder)
@require_POST
def toggle_resolved(request, message_id):
    """Close a conversation, or reopen a resolved one."""
    message = get_object_or_404(ContactMessage, id=message_id)
    if message.status == 'resolved':
        has_staff_reply = message.replies.filter(from_staff=True).exists()
        message.status = 'replied' if has_staff_reply else 'open'
    else:
        message.status = 'resolved'
    message.save(update_fields=['status'])

    return JsonResponse({'success': True, 'status': message.status})


@user_passes_test(is_founder)
@require_POST
def mark_urgent(request, message_id):
    """Mark a message as urgent"""
    message = get_object_or_404(ContactMessage, id=message_id)
    message.is_urgent = not message.is_urgent
    message.save(update_fields=['is_urgent'])

    return JsonResponse({
        'success': True,
        'is_urgent': message.is_urgent
    })


@user_passes_test(is_founder)
@require_POST
def mark_read(request, message_id):
    """Mark a message as read/unread"""
    message = get_object_or_404(ContactMessage, id=message_id)
    message.is_read = not message.is_read
    message.save(update_fields=['is_read'])

    return JsonResponse({
        'success': True,
        'is_read': message.is_read
    })
