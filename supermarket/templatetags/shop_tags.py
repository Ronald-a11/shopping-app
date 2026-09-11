from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Return the current query string with the given parameters replaced.

    Lets pagination links keep the active search, category and filter instead
    of resetting them. Passing None or '' removes a parameter.
    """
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        if value is None or value == '':
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()


@register.filter
def whatsapp_number(phone):
    """Digits in the international form wa.me expects, e.g. '0771…' -> '263771…'."""
    digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
    if digits.startswith('0'):
        digits = '263' + digits[1:]
    return digits


@register.simple_tag
def elided_page_range(page_obj, on_each_side=1, on_ends=1):
    """Page numbers with ellipses, e.g. 1 … 4 5 6 … 20."""
    return page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=on_each_side, on_ends=on_ends
    )
