"""The shop window: what the home page and the gallery put in front of people.

These cover the presentation rules that were wrong when the shop went live —
the same item listed twice at two prices, the front page opening with shampoo
and toilet paper, and pictures that came from guessed links to another website.
"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from supermarket.models import Category, Product


class CatalogueTestCase(TestCase):
    """A small shop: three aisles, with a local and an imported item in each."""

    def setUp(self):
        self.user = User.objects.create_user('shopper', password='shopping-pass')
        self.client.force_login(self.user)

        self.produce = Category.objects.create(name='Fresh Produce')
        self.bakery = Category.objects.create(name='Bakery & Grains')
        self.household = Category.objects.create(name='Household Items')

        self.tomatoes = self.make('Fresh Tomatoes (1kg)', self.produce, local=True)
        self.avocado = self.make('Avocado (3 pieces)', self.produce)
        self.bread = self.make('Brown Bread (1 loaf)', self.bakery, local=True)
        self.soap = self.make('Dish Soap (500ml)', self.household)

    def make(self, name, category, local=False, stock=10, available=True):
        return Product.objects.create(
            name=name, description=f'{name} for testing', category=category,
            price=2, stock_quantity=stock, is_local_product=local,
            is_available=available, image=f'/static/images/products/x.webp',
        )


class HomeShopWindowTests(CatalogueTestCase):
    def featured(self):
        return list(self.client.get(reverse('home')).context['featured_products'])

    def test_shows_one_product_from_each_aisle(self):
        featured = self.featured()

        self.assertEqual(len(featured), 3)
        self.assertEqual(
            {product.category.name for product in featured},
            {'Fresh Produce', 'Bakery & Grains', 'Household Items'},
        )

    def test_prefers_the_local_product_in_an_aisle(self):
        featured = self.featured()

        self.assertIn(self.tomatoes, featured)
        self.assertNotIn(self.avocado, featured)

    def test_skips_products_that_are_out_of_stock(self):
        self.tomatoes.stock_quantity = 0
        self.tomatoes.save(update_fields=['stock_quantity'])

        featured = self.featured()

        self.assertNotIn(self.tomatoes, featured)
        self.assertIn(self.avocado, featured, 'the aisle should fall back to its other product')

    def test_skips_hidden_products(self):
        self.tomatoes.is_available = False
        self.tomatoes.save(update_fields=['is_available'])

        self.assertNotIn(self.tomatoes, self.featured())

    def test_shows_at_most_eight(self):
        for index in range(12):
            category = Category.objects.create(name=f'Aisle {index}')
            self.make(f'Product {index}', category)

        self.assertEqual(len(self.featured()), 8)


class GalleryTests(CatalogueTestCase):
    def test_groups_the_catalogue_by_aisle(self):
        groups = self.client.get(reverse('gallery')).context['groups']

        self.assertEqual([group['name'] for group in groups],
                         ['Bakery & Grains', 'Fresh Produce', 'Household Items'])
        produce = next(g for g in groups if g['name'] == 'Fresh Produce')
        self.assertEqual([p.name for p in produce['products']],
                         ['Avocado (3 pieces)', 'Fresh Tomatoes (1kg)'])

    def test_leaves_out_hidden_products(self):
        self.soap.is_available = False
        self.soap.save(update_fields=['is_available'])

        response = self.client.get(reverse('gallery'))

        self.assertEqual(response.context['total_products'], 3)
        self.assertNotIn('Household Items', [g['name'] for g in response.context['groups']])

    def test_pictures_are_our_own_files(self):
        page = self.client.get(reverse('gallery')).content.decode()

        self.assertIn('/static/images/products/', page)
        self.assertNotIn('unsplash', page)

    def test_an_empty_aisle_gets_no_tab(self):
        Category.objects.create(name='Nothing Here')

        groups = self.client.get(reverse('gallery')).context['groups']

        self.assertNotIn('Nothing Here', [group['name'] for group in groups])

    def test_signed_out_visitors_are_sent_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(reverse('gallery'))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('gallery')}")


class TidyCatalogueCommandTests(CatalogueTestCase):
    """The one-off merge of the entries the old seed scripts duplicated."""

    def setUp(self):
        super().setUp()
        self.cereals = Category.objects.create(name='Grains & Cereals')
        # The pair the old scripts left behind: the same loaf twice, in two
        # aisles, at two prices.
        self.white_loaf = self.make('Fresh White Bread (1 loaf)', self.bakery, local=True)
        self.cheap_loaf = self.make('Bread (1 loaf)', self.cereals)

    def run_command(self, *args):
        out = StringIO()
        call_command('tidy_catalogue', *args, stdout=out)
        return out.getvalue()

    def test_moves_products_out_of_the_duplicate_aisle_and_removes_it(self):
        self.run_command()

        self.cheap_loaf.refresh_from_db()
        self.assertEqual(self.cheap_loaf.category, self.bakery)
        self.assertFalse(Category.objects.filter(name='Grains & Cereals').exists())

    def test_hides_the_duplicate_product_instead_of_deleting_it(self):
        self.run_command()

        self.cheap_loaf.refresh_from_db()
        self.assertFalse(self.cheap_loaf.is_available)
        self.assertTrue(Product.objects.filter(pk=self.cheap_loaf.pk).exists())

    def test_keeps_the_product_that_stays(self):
        self.run_command()

        self.white_loaf.refresh_from_db()
        self.assertTrue(self.white_loaf.is_available)

    def test_dry_run_changes_nothing(self):
        output = self.run_command('--dry-run')

        self.cheap_loaf.refresh_from_db()
        self.assertTrue(self.cheap_loaf.is_available)
        self.assertEqual(self.cheap_loaf.category, self.cereals)
        self.assertIn('Dry run', output)

    def test_running_it_twice_changes_nothing_the_second_time(self):
        self.run_command()

        second = self.run_command()

        self.assertIn('0 product(s) moved, 0 empty category(ies) removed, 0 duplicate', second)


class PopulateDataCommandTests(TestCase):
    """The seed a brand-new deployment starts from."""

    def run_command(self, *args):
        out = StringIO()
        call_command('populate_data', *args, stdout=out)
        return out.getvalue()

    def test_fills_an_empty_shop_from_the_fixture(self):
        self.run_command()

        self.assertGreater(Product.objects.count(), 0)
        self.assertGreater(Category.objects.count(), 0)

    def test_every_seeded_product_has_a_picture_of_our_own(self):
        self.run_command()

        for product in Product.objects.all():
            with self.subTest(product=product.name):
                self.assertTrue(product.image, f'{product.name} has no picture')
                self.assertTrue(product.image.startswith('/static/images/products/'),
                                f'{product.name} points outside the project: {product.image}')

    def test_leaves_an_existing_shop_alone(self):
        category = Category.objects.create(name='Fresh Produce')
        Product.objects.create(name='Fresh Tomatoes (1kg)', description='ours',
                               category=category, price=9, stock_quantity=3)

        output = self.run_command()

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Product.objects.get().price, 9)
        self.assertIn('nothing was loaded', output)

    def test_force_reloads_the_catalogue(self):
        category = Category.objects.create(name='Fresh Produce')
        Product.objects.create(name='Fresh Tomatoes (1kg)', description='ours',
                               category=category, price=9, stock_quantity=3)

        self.run_command('--force')

        self.assertGreater(Product.objects.count(), 1)
