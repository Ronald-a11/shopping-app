from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from supermarket.models import Category, Product

IMAGE_DIR = 'images/products'
DEFAULT_IMAGE = f'{IMAGE_DIR}/default.webp'


class Command(BaseCommand):
    help = 'Give products and categories the bundled placeholder images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Replace images that are already set',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without saving anything',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        verb = 'Would set' if dry_run else 'Set'

        categories_updated = 0
        for category in Category.objects.all():
            if category.image and not force:
                continue
            image_url = self.image_url(self.category_image_path(category))
            if category.image == image_url:
                continue
            self.stdout.write(f'{verb} category image: {category.name} -> {image_url}')
            if not dry_run:
                category.image = image_url
                category.save(update_fields=['image'])
            categories_updated += 1

        products_updated = 0
        products_skipped = 0
        for product in Product.objects.select_related('category'):
            if product.image and not force:
                products_skipped += 1
                continue
            image_url = self.image_url(self.product_image_path(product))
            if product.image == image_url:
                continue
            self.stdout.write(f'{verb} image for: {product.name} -> {image_url}')
            if not dry_run:
                product.image = image_url
                product.save(update_fields=['image'])
            products_updated += 1

        summary = (
            f'{products_updated} products and {categories_updated} categories'
            f' ({products_skipped} products already had an image)'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry run: would update {summary}.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {summary}!'))

    def product_image_path(self, product):
        """The product's own image, else its category's, else the default."""
        candidate = f'{IMAGE_DIR}/{slugify(product.name)}.webp'
        if finders.find(candidate):
            return candidate
        return self.category_image_path(product.category)

    def category_image_path(self, category):
        candidate = f'{IMAGE_DIR}/category-{slugify(category.name)}.webp'
        if finders.find(candidate):
            return candidate
        return DEFAULT_IMAGE

    def image_url(self, path):
        return settings.STATIC_URL + path
