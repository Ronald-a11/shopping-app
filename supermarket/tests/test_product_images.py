from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from supermarket.models import Category, Product

IMAGES = '/static/images/products/'


class AddProductImagesCommandTests(TestCase):
    def setUp(self):
        self.pantry = Category.objects.create(name='Pantry Staples')
        self.bakery = Category.objects.create(name='Bakery')
        self.garden = Category.objects.create(name='Garden Tools')

    def make_product(self, name, category, image=None):
        return Product.objects.create(
            name=name, description='Test product', category=category,
            price=1, image=image,
        )

    def run_command(self, *args):
        out = StringIO()
        call_command('add_product_images', *args, stdout=out)
        return out.getvalue()

    def test_product_with_matching_image_gets_it(self):
        rice = self.make_product('Rice (5kg)', self.pantry)

        self.run_command()

        rice.refresh_from_db()
        self.assertEqual(rice.image, IMAGES + 'rice-5kg.webp')

    def test_blank_string_image_counts_as_missing(self):
        rice = self.make_product('Rice (5kg)', self.pantry, image='')

        self.run_command()

        rice.refresh_from_db()
        self.assertEqual(rice.image, IMAGES + 'rice-5kg.webp')

    def test_falls_back_to_category_image(self):
        rolls = self.make_product('Sourdough Rolls', self.bakery)

        self.run_command()

        rolls.refresh_from_db()
        self.assertEqual(rolls.image, IMAGES + 'category-bakery.webp')

    def test_falls_back_to_default_image(self):
        hose = self.make_product('Garden Hose', self.garden)

        self.run_command()

        hose.refresh_from_db()
        self.assertEqual(hose.image, IMAGES + 'default.webp')

    def test_existing_image_kept_without_force(self):
        rice = self.make_product('Rice (5kg)', self.pantry, image='https://example.com/rice.jpg')

        self.run_command()

        rice.refresh_from_db()
        self.assertEqual(rice.image, 'https://example.com/rice.jpg')

    def test_existing_image_replaced_with_force(self):
        rice = self.make_product('Rice (5kg)', self.pantry, image='https://example.com/rice.jpg')
        self.bakery.image = 'https://example.com/bakery.jpg'
        self.bakery.save()

        self.run_command('--force')

        rice.refresh_from_db()
        self.bakery.refresh_from_db()
        self.assertEqual(rice.image, IMAGES + 'rice-5kg.webp')
        self.assertEqual(self.bakery.image, IMAGES + 'category-bakery.webp')

    def test_dry_run_saves_nothing(self):
        rice = self.make_product('Rice (5kg)', self.pantry)
        bread = self.make_product('Old Bread', self.bakery, image='https://example.com/bread.jpg')

        output = self.run_command('--dry-run', '--force')

        rice.refresh_from_db()
        bread.refresh_from_db()
        self.assertIsNone(rice.image)
        self.assertEqual(bread.image, 'https://example.com/bread.jpg')
        self.assertFalse(Category.objects.exclude(image=None).exists())
        self.assertIn('Would set image for: Rice (5kg)', output)
        self.assertIn('Dry run', output)

    def test_blank_category_images_are_filled(self):
        self.pantry.image = 'https://example.com/pantry.jpg'
        self.pantry.save()

        self.run_command()

        for category in (self.pantry, self.bakery, self.garden):
            category.refresh_from_db()
        self.assertEqual(self.pantry.image, 'https://example.com/pantry.jpg')
        self.assertEqual(self.bakery.image, IMAGES + 'category-bakery.webp')
        self.assertEqual(self.garden.image, IMAGES + 'default.webp')
