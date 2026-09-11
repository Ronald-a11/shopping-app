def cart_count(request):
    """Expose the cart's item count to every template for the header badge.

    Rendering it server-side avoids the badge flashing "0" while a separate
    request fetches the real number.
    """
    # Imported here to avoid a circular import at settings load time.
    from .views import get_cart

    cart = get_cart(request)
    return {'cart_count': cart.get_item_count() if cart else 0}
