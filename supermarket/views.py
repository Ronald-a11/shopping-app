from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http import JsonResponse, Http404, HttpResponseRedirect
from django.db.models import Q, Sum, F
from django.core.paginator import Paginator
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from datetime import timedelta
import logging
import urllib.parse
from .models import Product, Category, Cart, CartItem, Order, OrderItem, ContactMessage, UserProfile, DeliveryBooking
from .forms import (ContactForm, OrderForm, CustomUserCreationForm, UserProfileForm,
                    DeliveryBookingForm, DeliveryCancellationForm)

logger = logging.getLogger(__name__)

# Business contact number used for WhatsApp/SMS notifications.
NOTIFICATION_WHATSAPP_NUMBER = "263771938039"

# Delivery pricing by city (lowercased city name -> fee, estimated time).
DELIVERY_RATES = {
    'harare': (5.00, "1-2 hours"),
    'bulawayo': (5.00, "1-2 hours"),
    'gweru': (10.00, "2-4 hours"),
    'mutare': (10.00, "2-4 hours"),
    'kwekwe': (10.00, "2-4 hours"),
    'kadoma': (10.00, "2-4 hours"),
    'chinhoyi': (10.00, "2-4 hours"),
    'masvingo': (10.00, "2-4 hours"),
    'bindura': (10.00, "2-4 hours"),
    'marondera': (10.00, "2-4 hours"),
}
DEFAULT_DELIVERY_RATE = (15.00, "4-6 hours")


def _whatsapp_url(message):
    """Build a wa.me link for the given message body."""
    return f"https://wa.me/{NOTIFICATION_WHATSAPP_NUMBER}?text={urllib.parse.quote(message)}"


def _is_ajax(request):
    """True when the request was made by fetch/XHR rather than a plain form post."""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


def _parse_quantity(raw):
    """Parse a user-supplied quantity, returning None when it isn't a valid integer."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def send_whatsapp_notification(booking):
    """Send WhatsApp notification for delivery booking"""
    message = f"🚚 NEW DELIVERY BOOKING\n\n"
    message += f"👤 Customer: {booking.user.first_name} {booking.user.last_name}\n"
    message += f"📅 Date: {booking.delivery_date}\n"
    message += f"⏰ Time: {booking.get_time_slot_display()}\n"
    message += f"📍 Address: {booking.delivery_address}, {booking.delivery_city}\n"
    message += f"📞 Phone: {booking.delivery_phone}\n"
    message += f"💰 Delivery Fee: ${booking.delivery_fee}\n"
    message += f"⏱️ Estimated Time: {booking.estimated_delivery_time}\n"
    if booking.special_instructions:
        message += f"📝 Special Instructions: {booking.special_instructions}\n"
    if booking.order:
        message += f"📦 Order Total: ${booking.order.total_amount:.2f}"
    else:
        message += f"📦 Order: Standalone delivery booking"

    whatsapp_url = _whatsapp_url(message)

    # In a real implementation, you would send this notification
    # For now, we'll just mark it as sent
    booking.whatsapp_notification_sent = True
    booking.save(update_fields=['whatsapp_notification_sent', 'updated_at'])

    return whatsapp_url


def send_cancellation_whatsapp(booking):
    """Send WhatsApp notification for delivery cancellation"""
    message = f"❌ DELIVERY CANCELLED\n\n"
    message += f"👤 Customer: {booking.user.first_name} {booking.user.last_name}\n"
    message += f"📅 Original Date: {booking.delivery_date}\n"
    message += f"📍 Address: {booking.delivery_address}, {booking.delivery_city}\n"
    message += f"📞 Phone: {booking.delivery_phone}\n"
    message += f"❌ Reason: {booking.get_cancellation_reason_display()}\n"
    if booking.cancellation_notes:
        message += f"📝 Notes: {booking.cancellation_notes}\n"
    if booking.cancelled_at:
        message += f"🕐 Cancelled at: {booking.cancelled_at.strftime('%Y-%m-%d %H:%M')}"

    return _whatsapp_url(message)


def send_cancellation_whatsapp_with_info(booking_info):
    """Send WhatsApp notification for delivery cancellation with booking info"""
    message = f"❌ DELIVERY CANCELLED & DELETED\n\n"
    message += f"👤 Customer: {booking_info['user_name']}\n"
    message += f"📅 Original Date: {booking_info['delivery_date']}\n"
    message += f"📍 Address: {booking_info['delivery_address']}, {booking_info['delivery_city']}\n"
    message += f"📞 Phone: {booking_info['delivery_phone']}\n"
    message += f"❌ Reason: {booking_info['reason']}\n"
    if booking_info['notes']:
        message += f"📝 Notes: {booking_info['notes']}\n"
    message += f"🕐 Cancelled at: {timezone.now().strftime('%Y-%m-%d %H:%M')}"

    return _whatsapp_url(message)


def send_sms_notification(phone_number, message):
    """Send SMS notification"""
    # Create SMS URL for direct messaging
    sms_url = f"sms:{phone_number}?body={urllib.parse.quote(message)}"
    return sms_url


@login_required
def home(request):
    """Home page with featured products and categories - requires login"""
    featured_products = Product.objects.filter(is_available=True).select_related('category')[:8]
    categories = Category.objects.all()[:6]
    local_products = Product.objects.filter(
        is_local_product=True, is_available=True
    ).select_related('category')[:4]

    context = {
        'featured_products': featured_products,
        'categories': categories,
        'local_products': local_products,
    }
    return render(request, 'supermarket/home.html', context)


def product_list(request):
    """Product listing page with filtering and search"""
    products = Product.objects.filter(is_available=True).select_related('category')
    categories = Category.objects.all()

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(supplier__icontains=search_query)
        )

    # Category filtering
    category_id = request.GET.get('category')
    if category_id:
        # Ignore a non-numeric ?category= instead of raising ValueError.
        if str(category_id).isdigit():
            products = products.filter(category_id=category_id)
        else:
            category_id = None

    # Local products filter
    local_only = request.GET.get('local')
    if local_only:
        products = products.filter(is_local_product=True)

    # Enhanced filtering options
    filter_type = request.GET.get('filter_type')
    if filter_type == 'cheap':
        # Products under $10
        products = products.filter(price__lt=10)
    elif filter_type == 'expensive':
        # Products over $20
        products = products.filter(price__gt=20)
    elif filter_type == 'recent':
        # Products added in the last 7 days
        products = products.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif filter_type == 'available':
        # Products with stock
        products = products.filter(stock_quantity__gt=0)

    # Price sorting
    sort_by = request.GET.get('sort')
    sort_fields = {
        'price_low': 'price',
        'price_high': '-price',
        'name': 'name',
        'newest': '-created_at',
        'oldest': 'created_at',
    }
    products = products.order_by(sort_fields.get(sort_by, '-created_at'))

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    context = {
        'products': products,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'local_only': local_only,
        'filter_type': filter_type,
        'sort_by': sort_by,
    }
    return render(request, 'supermarket/product_list.html', context)


def product_detail(request, product_id):
    """Product detail page"""
    product = get_object_or_404(
        Product.objects.select_related('category'), id=product_id, is_available=True
    )
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(id=product_id)[:4]

    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'supermarket/product_detail.html', context)


def get_cart(request, create=False):
    """Return the cart belonging to this user/session, or None when there isn't one.

    Pass create=True only for actions that genuinely need a cart row, so that
    read-only endpoints don't litter the database with empty carts.
    """
    if request.user.is_authenticated:
        if create:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart
        return Cart.objects.filter(user=request.user).first()

    session_key = request.session.session_key
    if not session_key:
        if not create:
            return None
        request.session.create()
        session_key = request.session.session_key

    if create:
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
        return cart
    return Cart.objects.filter(session_key=session_key).first()


def get_or_create_cart(request):
    """Get or create cart for user or session"""
    return get_cart(request, create=True)


def get_owned_cart_item(request, item_id):
    """Fetch a cart item, but only if it belongs to the requesting user/session."""
    cart = get_cart(request)
    if cart is None:
        raise Http404("Cart item not found")
    return get_object_or_404(
        CartItem.objects.select_related('product'), id=item_id, cart=cart
    )


@require_POST
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, is_available=True)
    quantity = _parse_quantity(request.POST.get('quantity', 1))

    if quantity is None or quantity <= 0:
        message = 'Quantity must be a whole number greater than 0'
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': message}, status=400)
        messages.error(request, message)
        return redirect('product_detail', product_id=product_id)

    if quantity > product.stock_quantity:
        message = 'Not enough stock available'
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': message}, status=400)
        messages.error(request, message)
        return redirect('product_detail', product_id=product_id)

    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        cart_item.quantity = min(cart_item.quantity + quantity, product.stock_quantity)
        cart_item.save(update_fields=['quantity'])

    if _is_ajax(request):
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'count': cart.get_item_count(),
        })

    messages.success(request, f'{product.name} added to cart')
    return redirect('cart')


def cart_view(request):
    """Shopping cart page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product', 'product__category')

    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'supermarket/cart.html', context)


@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_owned_cart_item(request, item_id)
    quantity = _parse_quantity(request.POST.get('quantity', 1))

    if quantity is None:
        messages.error(request, 'Please enter a valid quantity')
    elif quantity <= 0:
        cart_item.delete()
        messages.success(request, 'Item removed from cart')
    elif quantity > cart_item.product.stock_quantity:
        messages.error(request, 'Not enough stock available')
    else:
        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity'])
        messages.success(request, 'Cart updated')

    return redirect('cart')


@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_owned_cart_item(request, item_id)
    cart_item.delete()
    messages.success(request, 'Item removed from cart')
    return redirect('cart')


def generate_order_number():
    """Generate an order number that isn't already taken."""
    for _ in range(10):
        candidate = get_random_string(8, allowed_chars='ABCDEFGHJKMNPQRSTUVWXYZ23456789')
        if not Order.objects.filter(order_number=candidate).exists():
            return candidate
    raise IntegrityError("Could not generate a unique order number")


class InsufficientStock(Exception):
    """Raised when a cart can no longer be fulfilled at checkout time."""

    def __init__(self, product):
        self.product = product
        super().__init__(f"Insufficient stock for {product.name}")


@login_required
def checkout(request):
    """Checkout page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product')

    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('cart')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request.user, cart, form)
            except InsufficientStock as exc:
                messages.error(
                    request,
                    f'Sorry, "{exc.product.name}" no longer has enough stock. '
                    'Please update your cart and try again.'
                )
                return redirect('cart')

            messages.success(request, f'Order {order.order_number} placed successfully!')
            return redirect('order_detail', order_id=order.id)
    else:
        form = OrderForm()

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'form': form,
    }
    return render(request, 'supermarket/checkout.html', context)


@transaction.atomic
def place_order(user, cart, form):
    """Turn a cart into an order, reserving stock atomically.

    Stock is decremented with a conditional UPDATE so two shoppers checking out
    at the same time can never oversell; if any line fails the whole
    transaction rolls back.
    """
    cart_items = list(cart.items.select_related('product'))

    order = form.save(commit=False)
    order.user = user
    order.order_number = generate_order_number()
    order.total_amount = cart.get_total()
    order.save()

    for cart_item in cart_items:
        product = cart_item.product
        updated = Product.objects.filter(
            id=product.id, stock_quantity__gte=cart_item.quantity
        ).update(stock_quantity=F('stock_quantity') - cart_item.quantity)

        if not updated:
            raise InsufficientStock(product)

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=cart_item.quantity,
            price=product.price
        )

    cart.items.all().delete()
    return order


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.select_related('product')

    context = {
        'order': order,
        'order_items': order_items,
    }
    return render(request, 'supermarket/order_detail.html', context)


@login_required
def cancel_order(request, order_id):
    """Cancel order and allow reordering"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Check if order can be cancelled (only pending orders)
    if order.status != 'pending':
        messages.error(request, 'This order cannot be cancelled. Only pending orders can be cancelled.')
        return redirect('order_detail', order_id=order.id)

    # Check if order has items
    if not order.items.exists():
        messages.error(request, 'This order has no items and cannot be cancelled.')
        return redirect('order_detail', order_id=order.id)

    if request.method == 'POST':
        restore_order_to_cart(request.user, order)
        messages.success(request, 'Order has been cancelled. Items have been added back to your cart for reordering.')
        return redirect('cart')

    context = {
        'order': order,
        'order_items': order.items.select_related('product'),
    }
    return render(request, 'supermarket/cancel_order.html', context)


@transaction.atomic
def restore_order_to_cart(user, order):
    """Return an order's items to the user's cart and release the reserved stock."""
    cart, _ = Cart.objects.get_or_create(user=user)

    for item in order.items.select_related('product'):
        # Give the reserved stock back so cancelled orders don't shrink inventory.
        Product.objects.filter(id=item.product_id).update(
            stock_quantity=F('stock_quantity') + item.quantity
        )

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=item.product,
            defaults={'quantity': item.quantity}
        )
        if not created:
            cart_item.quantity = F('quantity') + item.quantity
            cart_item.save(update_fields=['quantity'])

    order.delete()


@login_required
def order_history(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'orders': orders,
    }
    return render(request, 'supermarket/order_history.html', context)


def contact(request):
    """Contact page"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your message has been sent successfully! You can also send us a direct SMS at +263 771938039')
            return redirect('contact')
    else:
        form = ContactForm()

    context = {
        'form': form,
        'sms_url': send_sms_notification(
            NOTIFICATION_WHATSAPP_NUMBER, "Hello! I have an inquiry about your products."
        ),
    }
    return render(request, 'supermarket/contact.html', context)


@login_required
def about(request):
    """About page - requires login"""
    return render(request, 'supermarket/about.html')


@login_required
def gallery(request):
    """Image gallery page - requires login"""
    return render(request, 'supermarket/gallery.html')


def cart_count(request):
    """API endpoint to get cart count"""
    cart = get_cart(request)
    count = cart.get_item_count() if cart else 0
    return JsonResponse({'count': count})


# Authentication Views
def register(request):
    """User registration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.get_or_create(user=user)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    context = {'form': form}
    return render(request, 'supermarket/register.html', context)


def user_login(request):
    """User login"""
    redirect_to = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            if url_has_allowed_host_and_scheme(
                redirect_to, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return HttpResponseRedirect(redirect_to)
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'supermarket/login.html', {'next': redirect_to})


def user_logout(request):
    """User logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login')


@login_required
def profile(request):
    """User profile page"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)

    context = {'form': form, 'profile': profile}
    return render(request, 'supermarket/profile.html', context)


# Delivery Booking Views
@login_required
def delivery_booking(request):
    """Delivery booking page"""
    # Check if user has any orders
    user_orders = Order.objects.filter(user=request.user, status='pending')
    if not user_orders.exists():
        messages.warning(request, 'You need to place an order first before booking delivery. Please add items to your cart and complete an order.')
        return redirect('product_list')

    # Check if user already has a delivery booking for pending orders
    existing_booking = DeliveryBooking.objects.filter(user=request.user, order__in=user_orders).exists()
    if existing_booking:
        messages.info(request, 'You already have a delivery booking for your pending order. Please check your delivery bookings.')
        return redirect('delivery_bookings')

    if request.method == 'POST':
        form = DeliveryBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.user = request.user

            # Link to the most recent pending order
            booking.order = user_orders.order_by('-created_at').first()

            # Calculate delivery fee based on city (simplified)
            fee, eta = DELIVERY_RATES.get(
                booking.delivery_city.strip().lower(), DEFAULT_DELIVERY_RATE
            )
            booking.delivery_fee = fee
            booking.estimated_delivery_time = eta

            booking.save()

            # Send WhatsApp notification with delivery time
            try:
                send_whatsapp_notification(booking)
            except Exception:
                # Log the error but don't fail the booking
                logger.exception("WhatsApp notification failed for booking %s", booking.pk)

            messages.success(request, f'Delivery booking confirmed for {booking.delivery_date}! Estimated delivery time: {booking.estimated_delivery_time}')
            return redirect('delivery_bookings')
    else:
        form = DeliveryBookingForm()

    context = {
        'form': form,
        'user_orders': user_orders,
        'has_orders': True,
    }
    return render(request, 'supermarket/delivery_booking.html', context)


@login_required
def delivery_bookings(request):
    """User's delivery bookings"""
    bookings = DeliveryBooking.objects.filter(user=request.user).select_related('order').order_by('-created_at')

    context = {'bookings': bookings}
    return render(request, 'supermarket/delivery_bookings.html', context)


@login_required
def delivery_booking_detail(request, booking_id):
    """Delivery booking detail page"""
    booking = get_object_or_404(
        DeliveryBooking.objects.select_related('order'), id=booking_id, user=request.user
    )

    context = {'booking': booking}
    return render(request, 'supermarket/delivery_booking_detail.html', context)


@login_required
def cancel_delivery(request, booking_id):
    """Cancel and delete delivery booking"""
    booking = get_object_or_404(DeliveryBooking, id=booking_id, user=request.user)

    if not booking.can_be_cancelled():
        messages.error(request, 'This delivery cannot be cancelled.')
        return redirect('delivery_bookings')

    if request.method == 'POST':
        form = DeliveryCancellationForm(request.POST)
        if form.is_valid():
            # Store booking info for notification before deletion
            booking_info = {
                'user_name': booking.user.get_full_name() or booking.user.username,
                'delivery_date': booking.delivery_date,
                'delivery_address': booking.delivery_address,
                'delivery_city': booking.delivery_city,
                'delivery_phone': booking.delivery_phone,
                'reason': dict(DeliveryBooking.CANCELLATION_REASONS).get(
                    form.cleaned_data['cancellation_reason'],
                    form.cleaned_data['cancellation_reason'],
                ),
                'notes': form.cleaned_data['cancellation_notes'],
            }

            # Send cancellation WhatsApp notification before deletion
            try:
                send_cancellation_whatsapp_with_info(booking_info)
            except Exception:
                # Log the error but don't fail the cancellation
                logger.exception("WhatsApp cancellation notification failed for booking %s", booking.pk)

            # Delete the delivery booking
            booking.delete()

            messages.success(request, 'Delivery has been cancelled and deleted successfully.')
            return redirect('delivery_bookings')
    else:
        form = DeliveryCancellationForm()

    return render(request, 'supermarket/cancel_delivery.html', {
        'booking': booking,
        'form': form
    })
