from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import datetime, timedelta
import urllib.parse
from .models import Product, Category, Cart, CartItem, Order, OrderItem, ContactMessage, UserProfile, DeliveryBooking
from .forms import ContactForm, OrderForm, CustomUserCreationForm, UserProfileForm, DeliveryBookingForm


def send_whatsapp_notification(booking):
    """Send WhatsApp notification for delivery booking"""
    whatsapp_number = "263771938039"  # Your WhatsApp number
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
    
    # Create WhatsApp URL
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(message)}"
    
    # In a real implementation, you would send this notification
    # For now, we'll just mark it as sent
    booking.whatsapp_notification_sent = True
    booking.save()
    
    return whatsapp_url


def send_cancellation_whatsapp(booking):
    """Send WhatsApp notification for delivery cancellation"""
    whatsapp_number = "263771938039"
    message = f"❌ DELIVERY CANCELLED\n\n"
    message += f"👤 Customer: {booking.user.first_name} {booking.user.last_name}\n"
    message += f"📅 Original Date: {booking.delivery_date}\n"
    message += f"📍 Address: {booking.delivery_address}, {booking.delivery_city}\n"
    message += f"📞 Phone: {booking.delivery_phone}\n"
    message += f"❌ Reason: {booking.get_cancellation_reason_display()}\n"
    if booking.cancellation_notes:
        message += f"📝 Notes: {booking.cancellation_notes}\n"
    message += f"🕐 Cancelled at: {booking.cancelled_at.strftime('%Y-%m-%d %H:%M')}"
    
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(message)}"
    return whatsapp_url


def send_cancellation_whatsapp_with_info(booking_info):
    """Send WhatsApp notification for delivery cancellation with booking info"""
    whatsapp_number = "263771938039"
    message = f"❌ DELIVERY CANCELLED & DELETED\n\n"
    message += f"👤 Customer: {booking_info['user_name']}\n"
    message += f"📅 Original Date: {booking_info['delivery_date']}\n"
    message += f"📍 Address: {booking_info['delivery_address']}, {booking_info['delivery_city']}\n"
    message += f"📞 Phone: {booking_info['delivery_phone']}\n"
    message += f"❌ Reason: {booking_info['reason']}\n"
    if booking_info['notes']:
        message += f"📝 Notes: {booking_info['notes']}\n"
    message += f"🕐 Cancelled at: {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(message)}"
    return whatsapp_url


def send_sms_notification(phone_number, message):
    """Send SMS notification"""
    # Create SMS URL for direct messaging
    sms_url = f"sms:{phone_number}?body={urllib.parse.quote(message)}"
    return sms_url


@login_required
def home(request):
    """Home page with featured products and categories - requires login"""
    featured_products = Product.objects.filter(is_available=True)[:8]
    categories = Category.objects.all()[:6]
    local_products = Product.objects.filter(is_local_product=True, is_available=True)[:4]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
        'local_products': local_products,
    }
    return render(request, 'supermarket/home.html', context)


def product_list(request):
    """Product listing page with filtering and search"""
    products = Product.objects.filter(is_available=True)
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
        products = products.filter(category_id=category_id)
    
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
        from datetime import datetime, timedelta
        recent_date = datetime.now() - timedelta(days=7)
        products = products.filter(created_at__gte=recent_date)
    elif filter_type == 'available':
        # Products with stock
        products = products.filter(stock_quantity__gt=0)
    
    # Price sorting
    sort_by = request.GET.get('sort')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'oldest':
        products = products.order_by('created_at')
    else:
        products = products.order_by('-created_at')
    
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
    product = get_object_or_404(Product, id=product_id, is_available=True)
    related_products = Product.objects.filter(
        category=product.category, 
        is_available=True
    ).exclude(id=product_id)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    return render(request, 'supermarket/product_detail.html', context)


def get_or_create_cart(request):
    """Get or create cart for user or session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_available=True)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            messages.error(request, 'Quantity must be greater than 0')
            return redirect('product_detail', product_id=product_id)
        
        if quantity > product.stock_quantity:
            messages.error(request, 'Not enough stock available')
            return redirect('product_detail', product_id=product_id)
        
        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.stock_quantity:
                cart_item.quantity = product.stock_quantity
            cart_item.save()
        
        messages.success(request, f'{product.name} added to cart')
        
        if request.headers.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Product added to cart'})
        
        return redirect('cart')
    
    return redirect('product_detail', product_id=product_id)


def cart_view(request):
    """Shopping cart page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'supermarket/cart.html', context)


def update_cart_item(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id)
        quantity = int(request.POST.get('quantity', 1))
        
        if quantity <= 0:
            cart_item.delete()
            messages.success(request, 'Item removed from cart')
        elif quantity > cart_item.product.stock_quantity:
            messages.error(request, 'Not enough stock available')
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated')
        
        return redirect('cart')
    
    return redirect('cart')


def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()
    messages.success(request, 'Item removed from cart')
    return redirect('cart')


@login_required
def checkout(request):
    """Checkout page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty')
        return redirect('cart')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Create order
            order = form.save(commit=False)
            order.user = request.user
            order.order_number = get_random_string(8).upper()
            order.total_amount = cart.get_total()
            order.save()
            
            # Create order items
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
            
            # Clear cart
            cart.items.all().delete()
            
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


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items = order.items.all()
    
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
    order_items = order.items.all()
    if not order_items.exists():
        messages.error(request, 'This order has no items and cannot be cancelled.')
        return redirect('order_detail', order_id=order.id)
    
    if request.method == 'POST':
        # Store order items for reordering
        order_items = order.items.all()
        
        # Create new cart for the user
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Add items back to cart
        for item in order_items:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not created:
                cart_item.quantity += item.quantity
                cart_item.save()
        
        # Delete the order
        order.delete()
        
        messages.success(request, 'Order has been cancelled. Items have been added back to your cart for reordering.')
        return redirect('cart')
    
    context = {
        'order': order,
        'order_items': order.items.all(),
    }
    return render(request, 'supermarket/cancel_order.html', context)


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
            contact_message = form.save()
            
            # Create SMS message
            sms_message = f"New inquiry from {contact_message.name} ({contact_message.phone_number}):\n"
            sms_message += f"Subject: {contact_message.subject}\n"
            sms_message += f"Message: {contact_message.message}"
            
            # Generate SMS URL
            sms_url = send_sms_notification("263771938039", sms_message)
            
            messages.success(request, f'Your message has been sent successfully! You can also send us a direct SMS at +263 771938039')
            return redirect('contact')
    else:
        form = ContactForm()
    
    context = {
        'form': form,
        'sms_url': send_sms_notification("263771938039", "Hello! I have an inquiry about your products.")
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
    cart = get_or_create_cart(request)
    count = cart.items.aggregate(total=Sum('quantity'))['total'] or 0
    return JsonResponse({'count': count})


# Authentication Views
def register(request):
    """User registration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    
    context = {'form': form}
    return render(request, 'supermarket/register.html', context)


def user_login(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'supermarket/login.html')


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
            latest_order = user_orders.order_by('-created_at').first()
            booking.order = latest_order
            
            # Calculate delivery fee based on city (simplified)
            city = booking.delivery_city.lower()
            if city in ['harare', 'bulawayo']:
                booking.delivery_fee = 5.00
                booking.estimated_delivery_time = "1-2 hours"
            elif city in ['gweru', 'mutare', 'kwekwe', 'kadoma', 'chinhoyi', 'masvingo', 'bindura', 'marondera']:
                booking.delivery_fee = 10.00
                booking.estimated_delivery_time = "2-4 hours"
            else:
                booking.delivery_fee = 15.00
                booking.estimated_delivery_time = "4-6 hours"
            
            booking.save()
            
            # Send WhatsApp notification with delivery time
            try:
                send_whatsapp_notification(booking)
            except Exception as e:
                # Log the error but don't fail the booking
                print(f"WhatsApp notification failed: {e}")
                pass
            
            messages.success(request, f'Delivery booking confirmed for {booking.delivery_date}! Estimated delivery time: {booking.estimated_delivery_time}')
            return redirect('delivery_bookings')
    else:
        form = DeliveryBookingForm()
    
    context = {
        'form': form,
        'user_orders': user_orders,
        'has_orders': user_orders.exists()
    }
    return render(request, 'supermarket/delivery_booking.html', context)


@login_required
def delivery_bookings(request):
    """User's delivery bookings"""
    bookings = DeliveryBooking.objects.filter(user=request.user).order_by('-created_at')
    
    context = {'bookings': bookings}
    return render(request, 'supermarket/delivery_bookings.html', context)


@login_required
def delivery_booking_detail(request, booking_id):
    """Delivery booking detail page"""
    booking = get_object_or_404(DeliveryBooking, id=booking_id, user=request.user)
    
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
            reason = form.cleaned_data['cancellation_reason']
            notes = form.cleaned_data['cancellation_notes']
            
            # Store booking info for notification before deletion
            booking_info = {
                'user_name': f"{booking.user.first_name} {booking.user.last_name}",
                'delivery_date': booking.delivery_date,
                'delivery_address': booking.delivery_address,
                'delivery_city': booking.delivery_city,
                'delivery_phone': booking.delivery_phone,
                'reason': reason,
                'notes': notes
            }
            
            # Send cancellation WhatsApp notification before deletion
            try:
                send_cancellation_whatsapp_with_info(booking_info)
            except Exception as e:
                # Log the error but don't fail the cancellation
                print(f"WhatsApp cancellation notification failed: {e}")
                pass
            
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