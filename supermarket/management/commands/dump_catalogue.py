"""Write the shop's current categories and products to the seed fixture.

Run this after adding a product, changing a price or editing a picture, so a
fresh install (``populate_data``) sets up the same shop::

    python manage.py dump_catalogue

Hidden products are left out — a new shop should not start with things that are
not for sale. Orders, accounts, messages and deliveries are never included.
"""
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand

from supermarket.models import Category, Product

FIXTURE = Path(__file__).resolve().parents[2] / 'fixtures' / 'catalogue.json'


class Command(BaseCommand):
    help = "Write the current catalogue to supermarket/fixtures/catalogue.json"

    def handle(self, *args, **options):
        categories = list(Category.objects.order_by('id'))
        products = list(Product.objects.filter(is_available=True).order_by('id'))

        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(
            serializers.serialize('json', categories + products, indent=2),
            encoding='utf-8',
        )
        self.stdout.write(self.style.SUCCESS(
            f'Wrote {len(categories)} categories and {len(products)} products to {FIXTURE.name}.'))
