from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.db.models import Q
from .models import ContactMessage, DeliveryBooking, Order
from django.core.paginator import Paginator


def is_founder(user):
    """Check if the user is allowed into the founder dashboard.

    This used to compare the profile's phone number against a hardcoded
    value. That number is printed on the public contact and delivery pages,
    and any registered user could type it into their own profile to grant
    themselves access to every customer's messages, orders and addresses.
    Staff status is set by a superuser and cannot be self-assigned.
    """
    return user.is_authenticated and user.is_staff


@user_passes_test(is_founder)
def founder_dashboard(request):
    """Founder's dashboard with all messages and complaints"""
    # Get all contact messages
    messages = ContactMessage.objects.all().order_by('-created_at')
    
    # Get urgent messages
    urgent_messages = messages.filter(is_urgent=True)
    
    # Get complaints
    complaints = messages.filter(message_type='complaint')
    
    # Get recent deliveries
    recent_deliveries = DeliveryBooking.objects.all().order_by('-created_at')[:10]
    
    # Get recent orders
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # Statistics
    total_messages = messages.count()
    unread_messages = messages.filter(is_read=False).count()
    total_complaints = complaints.count()
    urgent_count = urgent_messages.count()
    
    # Pagination for messages
    paginator = Paginator(messages, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    context = {
        'messages': messages_page,
        'urgent_messages': urgent_messages,
        'complaints': complaints,
        'recent_deliveries': recent_deliveries,
        'recent_orders': recent_orders,
        'total_messages': total_messages,
        'unread_messages': unread_messages,
        'total_complaints': total_complaints,
        'urgent_count': urgent_count,
    }
    
    return render(request, 'supermarket/founder_dashboard.html', context)


@user_passes_test(is_founder)
def message_detail(request, message_id):
    """Detailed view of a specific message"""
    message = get_object_or_404(ContactMessage, id=message_id)
    
    # Mark as read when viewed
    if not message.is_read:
        message.is_read = True
        message.save()
    
    context = {
        'message': message,
    }
    
    return render(request, 'supermarket/message_detail.html', context)


@user_passes_test(is_founder)
def mark_urgent(request, message_id):
    """Mark a message as urgent"""
    message = get_object_or_404(ContactMessage, id=message_id)
    message.is_urgent = not message.is_urgent
    message.save()
    
    return JsonResponse({
        'success': True,
        'is_urgent': message.is_urgent
    })


@user_passes_test(is_founder)
def mark_read(request, message_id):
    """Mark a message as read/unread"""
    message = get_object_or_404(ContactMessage, id=message_id)
    message.is_read = not message.is_read
    message.save()
    
    return JsonResponse({
        'success': True,
        'is_read': message.is_read
    })
