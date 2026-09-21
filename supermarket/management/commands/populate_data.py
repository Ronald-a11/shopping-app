"""Fill an empty shop with the JKC Supermarket catalogue.

The catalogue itself lives in ``supermarket/fixtures/catalogue.json`` — the nine
categories and the products on sale, with their prices, stock, suppliers and
pictures. Keeping it in a fixture means a new machine or a new deployment gets
exactly the shop we have here, rather than a hand-written sample that drifts
away from it over time.

To refresh the fixture after changing the catalogue::

    python manage.py dump_catalogue
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

from supermarket.models import Category, Product


class Command(BaseCommand):
    help = 'Fill an empty shop with the JKC Supermarket catalogue'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Load it even if there are already products. Prices, stock and '
                 'pictures are reset to the ones in the fixture; orders are untouched.')

    def handle(self, *args, **options):
        existing = Product.objects.count()
        if existing and not options['force']:
            self.stdout.write(self.style.WARNING(
                f'The shop already has {existing} products, so nothing was loaded.\n'
                'Use --force to reset them to the catalogue in '
                'supermarket/fixtures/catalogue.json.'))
            return

        call_command('loaddata', 'catalogue', verbosity=0)
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {Category.objects.count()} categories and '
            f'{Product.objects.count()} products.'))
