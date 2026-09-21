"""Merge the categories and products that earlier seed scripts duplicated.

The shop grew several near-identical entries — "Fresh Produce" *and* "Fruits &
Vegetables", "Bread (1 loaf)" at $1.00 next to "Fresh White Bread (1 loaf)" at
$2.20 — because half a dozen one-off scripts each added their own version of the
catalogue. Shoppers saw the same item twice at two prices.

Nothing is deleted except an empty category:

* products move to the surviving category,
* duplicate products are **hidden** (``is_available = False``), which keeps
  their order history intact and can be undone from Django admin by ticking
  "Is available" again.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from supermarket.models import Category, Product

# duplicate category -> the one to keep
CATEGORY_MERGES = {
    'Fruits & Vegetables': 'Fresh Produce',
    'Grains & Cereals': 'Bakery & Grains',
    'Dairy Products': 'Dairy & Eggs',
}

# product to hide -> the one that stays, and why
PRODUCT_MERGES = {
    'Cabbage (1 head)': ('Green Cabbage (1 head)', 'same vegetable, $3.20 against $1.20'),
    'Bread (1 loaf)': ('Fresh White Bread (1 loaf)', 'same loaf, $1.00 against $2.20'),
    'Toilet Paper (4 pack)': ('Toilet Paper (4 rolls)', 'same four rolls, $6.80 against $3.50'),
    'Toothpaste (100ml)': ('Toothpaste (100g)', 'same tube, and 100g belongs in Personal Care'),
}


class Command(BaseCommand):
    help = 'Merge the duplicate categories and products left by the old seed scripts'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would change without saving anything.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        moved = hidden = removed = 0

        with transaction.atomic():
            for duplicate_name, keeper_name in CATEGORY_MERGES.items():
                duplicate = Category.objects.filter(name=duplicate_name).first()
                keeper = Category.objects.filter(name=keeper_name).first()
                if duplicate is None:
                    continue
                if keeper is None:
                    self.stdout.write(self.style.WARNING(
                        f'Leaving "{duplicate_name}" alone: there is no "{keeper_name}" to merge it into.'))
                    continue

                products = list(duplicate.products.all())
                for product in products:
                    self.stdout.write(f'  {product.name}: {duplicate_name} -> {keeper_name}')
                    if not dry_run:
                        product.category = keeper
                        product.save(update_fields=['category'])
                    moved += 1

                self.stdout.write(f'Category "{duplicate_name}" is now empty - removing it.')
                if not dry_run:
                    duplicate.delete()
                removed += 1

            for hide_name, (keep_name, reason) in PRODUCT_MERGES.items():
                to_hide = Product.objects.filter(name=hide_name).first()
                keeper = Product.objects.filter(name=keep_name).first()
                if to_hide is None or keeper is None:
                    continue
                if not to_hide.is_available:
                    continue
                self.stdout.write(f'Hiding "{hide_name}" - keeping "{keep_name}" ({reason}).')
                if not dry_run:
                    to_hide.is_available = False
                    to_hide.save(update_fields=['is_available'])
                hidden += 1

            if dry_run:
                transaction.set_rollback(True)

        summary = (f'{moved} product(s) moved, {removed} empty category(ies) removed, '
                   f'{hidden} duplicate product(s) hidden')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Dry run: would have made {summary}. Nothing was saved.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done - {summary}.'))
            self.stdout.write('A hidden product is not gone. To put one back in the shop, tick '
                              '"Is available" for it in Django admin.')
