import hashlib
from pathlib import Path
from urllib.parse import quote

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

_STAMPS = {}


@register.simple_tag
def static_versioned(path):
    """Like {% static %}, but with a stamp that changes when the file does.

    A browser that picked up a half-written stylesheet - which happens while
    Tailwind is rebuilding one - would otherwise keep reusing it, and the page
    renders with its colours but none of its layout. A new stamp gives the
    file a new address, so a stale or partial copy can never be reused.

    Off the development server the file names already carry a hash, so this
    returns the plain URL.
    """
    url = static(path)
    if not settings.DEBUG:
        return url

    found = finders.find(path)
    if not found:
        return url

    file = Path(found)
    try:
        info = file.stat()
    except OSError:
        return url

    key = (str(file), info.st_mtime_ns, info.st_size)
    stamp = _STAMPS.get(key)
    if stamp is None:
        digest = hashlib.blake2b(file.read_bytes(), digest_size=6).hexdigest()
        _STAMPS.clear()          # only the current version of each file matters
        _STAMPS[key] = stamp = digest
    return f'{url}?v={stamp}'


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
def whatsapp_url(phone, text=''):
    """wa.me link to the number, optionally with the message pre-filled."""
    url = f"https://wa.me/{whatsapp_number(phone)}"
    return f"{url}?text={quote(text, safe='')}" if text else url


@register.simple_tag
def sms_url(phone, text=''):
    """sms: link to the number, optionally with the message pre-filled."""
    number = whatsapp_number(phone)
    url = f"sms:+{number}" if number else 'sms:'
    return f"{url}?body={quote(text, safe='')}" if text else url


@register.simple_tag
def elided_page_range(page_obj, on_each_side=1, on_ends=1):
    """Page numbers with ellipses, e.g. 1 … 4 5 6 … 20."""
    return page_obj.paginator.get_elided_page_range(
        page_obj.number, on_each_side=on_each_side, on_ends=on_ends
    )
