def cart_count(request):
    """Expose the cart's item count to every template for the header badge.

    Rendering it server-side avoids the badge flashing "0" while a separate
    request fetches the real number.
    """
    # Imported here to avoid a circular import at settings load time.
    from .views import get_cart

    cart = get_cart(request)
    return {'cart_count': cart.get_item_count() if cart else 0}


def message_notifications(request):
    """Count staff replies the logged-in customer hasn't opened yet."""
    if not request.user.is_authenticated:
        return {'unread_replies': 0}

    from .models import MessageReply

    count = MessageReply.objects.filter(
        message__user=request.user, from_staff=True, read_by_customer=False
    ).count()
    return {'unread_replies': count}
