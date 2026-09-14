from django.contrib import messages as flash
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import StaffReplyForm
from .models import ContactMessage, DeliveryBooking, Order


# Quick filters offered on the dashboard's message tabs.
MESSAGE_FILTERS = {
    'open': Q(status='open'),
    'unread': Q(is_read=False),
    'complaints': Q(message_type='complaint'),
    'urgent': Q(is_urgent=True),
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
    recent_deliveries = DeliveryBooking.objects.select_related('user').order_by('-created_at')[:10]

    # Get recent orders
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]

    # Statistics
    total_messages = messages.count()
    unread_messages = messages.filter(is_read=False).count()
    total_complaints = complaints.count()
    urgent_count = urgent_messages.count()
    open_count = messages.filter(status='open').count()

    # Apply the selected quick filter to the message list
    active_filter = request.GET.get('filter', 'all')
    if active_filter in MESSAGE_FILTERS:
        filtered_messages = messages.filter(MESSAGE_FILTERS[active_filter])
    else:
        active_filter = 'all'
        filtered_messages = messages
    filtered_messages = filtered_messages.annotate(reply_count=Count('replies'))

    # Pagination for messages
    paginator = Paginator(filtered_messages, 20)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)

    context = {
        # Not called `messages`: that name is Django's flash messages, which
        # base.html renders as toasts.
        'contact_messages': messages_page,
        'active_filter': active_filter,
        'urgent_messages': urgent_messages,
        'complaints': complaints,
        'recent_deliveries': recent_deliveries,
        'recent_orders': recent_orders,
        'total_messages': total_messages,
        'unread_messages': unread_messages,
        'total_complaints': total_complaints,
        'urgent_count': urgent_count,
        'open_count': open_count,
    }

    return render(request, 'supermarket/founder_dashboard.html', context)


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
