from django.core.management.base import BaseCommand
from supermarket.models import Category, Product
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add more Zimbabwean products to the database'

    def handle(self, *args, **options):
        # Get existing categories
        try:
            fresh_produce = Category.objects.get(name='Fresh Produce')
            meat_poultry = Category.objects.get(name='Meat & Poultry')
            dairy_eggs = Category.objects.get(name='Dairy & Eggs')
            bakery_grains = Category.objects.get(name='Bakery & Grains')
            pantry_staples = Category.objects.get(name='Pantry Staples')
            beverages = Category.objects.get(name='Beverages')
            snacks_confectionery = Category.objects.get(name='Snacks & Confectionery')
            household_items = Category.objects.get(name='Household Items')
        except Category.DoesNotExist:
            self.stdout.write(self.style.ERROR('Categories not found. Please run update_zim_products_2024 first.'))
            return

        # Additional Zimbabwean products
        zim_products = [
            # Fresh Produce - More Zimbabwe varieties
            {
                'name': 'Sweet Potatoes (1kg)',
                'description': 'Fresh sweet potatoes, perfect for roasting and traditional dishes',
                'category': fresh_produce,
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Mashonaland Farms'
            },
            {
                'name': 'Green Beans (500g)',
                'description': 'Fresh green beans, perfect for stir-fries and salads',
                'category': fresh_produce,
                'price': Decimal('2.20'),
                'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Local Vegetable Growers'
            },
            {
                'name': 'Spinach (1 bunch)',
                'description': 'Fresh spinach leaves, rich in iron and vitamins',
                'category': fresh_produce,
                'price': Decimal('1.80'),
                'image': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Local Vegetable Growers'
            },
            {
                'name': 'Avocado (3 pieces)',
                'description': 'Fresh avocados, perfect for salads and healthy eating',
                'category': fresh_produce,
                'price': Decimal('4.50'),
                'image': 'https://images.unsplash.com/photo-1523049673857-eb18f1d7b578?w=400&h=300&fit=crop',
                'stock_quantity': 15,
                'is_local_product': True,
                'supplier': 'Mashonaland Farms'
            },

            # Meat & Poultry - More Zimbabwe options
            {
                'name': 'Goat Meat (1kg)',
                'description': 'Fresh goat meat, popular in traditional Zimbabwe cuisine',
                'category': meat_poultry,
                'price': Decimal('9.50'),
                'image': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop',
                'stock_quantity': 12,
                'is_local_product': True,
                'supplier': 'Local Goat Farm'
            },
            {
                'name': 'Fish (Tilapia) (500g)',
                'description': 'Fresh tilapia fish from Zimbabwe waters',
                'category': meat_poultry,
                'price': Decimal('6.80'),
                'image': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400&h=300&fit=crop',
                'stock_quantity': 18,
                'is_local_product': True,
                'supplier': 'Zimbabwe Fisheries'
            },

            # Dairy & Eggs - More local options
            {
                'name': 'Yogurt (500ml)',
                'description': 'Fresh yogurt from local dairy farms',
                'category': dairy_eggs,
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Zimbabwe Dairy Co.'
            },
            {
                'name': 'Sour Milk (500ml)',
                'description': 'Traditional sour milk, popular in Zimbabwe',
                'category': dairy_eggs,
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Zimbabwe Dairy Co.'
            },

            # Bakery & Grains - Traditional Zimbabwe foods
            {
                'name': 'Sadza (Ready Mix) (1kg)',
                'description': 'Traditional Zimbabwe sadza ready mix',
                'category': bakery_grains,
                'price': Decimal('3.20'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 35,
                'is_local_product': True,
                'supplier': 'Zimbabwe Grain Co.'
            },
            {
                'name': 'Sorghum Meal (1kg)',
                'description': 'Traditional sorghum meal for healthy eating',
                'category': bakery_grains,
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Zimbabwe Grain Co.'
            },
            {
                'name': 'Millet (1kg)',
                'description': 'Traditional millet grain, nutritious and healthy',
                'category': bakery_grains,
                'price': Decimal('3.80'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Zimbabwe Grain Co.'
            },

            # Pantry Staples - Zimbabwe essentials
            {
                'name': 'Peanut Butter (500g)',
                'description': 'Creamy peanut butter, locally made',
                'category': pantry_staples,
                'price': Decimal('4.20'),
                'image': 'https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Zimbabwe Nut Co.'
            },
            {
                'name': 'Honey (250g)',
                'description': 'Pure natural honey from Zimbabwe beekeepers',
                'category': pantry_staples,
                'price': Decimal('5.50'),
                'image': 'https://images.unsplash.com/photo-1587049352846-4a222e784d38?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Zimbabwe Honey Co.'
            },
            {
                'name': 'Groundnuts (500g)',
                'description': 'Roasted groundnuts, perfect for snacking',
                'category': pantry_staples,
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Zimbabwe Nut Co.'
            },

            # Beverages - Zimbabwe drinks
            {
                'name': 'Maheu (500ml)',
                'description': 'Traditional Zimbabwe maheu drink',
                'category': beverages,
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400&h=300&fit=crop',
                'stock_quantity': 40,
                'is_local_product': True,
                'supplier': 'Zimbabwe Beverage Co.'
            },
            {
                'name': 'Mango Juice (1L)',
                'description': 'Fresh mango juice from local mangoes',
                'category': beverages,
                'price': Decimal('4.80'),
                'image': 'https://images.unsplash.com/photo-1613478223719-4ab8038ded72?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Zimbabwe Juice Co.'
            },
            {
                'name': 'Passion Fruit Juice (1L)',
                'description': 'Refreshing passion fruit juice',
                'category': beverages,
                'price': Decimal('5.20'),
                'image': 'https://images.unsplash.com/photo-1613478223719-4ab8038ded72?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Zimbabwe Juice Co.'
            },

            # Snacks & Confectionery - Zimbabwe treats
            {
                'name': 'Maputi (Popcorn) (200g)',
                'description': 'Traditional Zimbabwe popcorn snack',
                'category': snacks_confectionery,
                'price': Decimal('2.20'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 35,
                'is_local_product': True,
                'supplier': 'Zimbabwe Snacks Co.'
            },
            {
                'name': 'Roasted Maize (500g)',
                'description': 'Traditional roasted maize snack',
                'category': snacks_confectionery,
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Zimbabwe Snacks Co.'
            },
            {
                'name': 'Dried Mango (200g)',
                'description': 'Sweet dried mango slices',
                'category': snacks_confectionery,
                'price': Decimal('4.50'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Zimbabwe Dried Fruits Co.'
            },

            # Household Items - Zimbabwe brands
            {
                'name': 'Candles (Pack of 6)',
                'description': 'Emergency candles for power outages',
                'category': household_items,
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop',
                'stock_quantity': 40,
                'is_local_product': True,
                'supplier': 'Zimbabwe Candle Co.'
            },
            {
                'name': 'Matches (Box of 10)',
                'description': 'Safety matches for lighting',
                'category': household_items,
                'price': Decimal('1.50'),
                'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop',
                'stock_quantity': 50,
                'is_local_product': True,
                'supplier': 'Zimbabwe Match Co.'
            }
        ]

        created_count = 0
        for product_data in zim_products:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'category': product_data['category'],
                    'price': product_data['price'],
                    'image': product_data['image'],
                    'stock_quantity': product_data['stock_quantity'],
                    'is_available': True,
                    'is_local_product': product_data['is_local_product'],
                    'supplier': product_data['supplier']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created Zimbabwe product: {product.name} - ${product.price}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully added {created_count} new Zimbabwean products to the database!')
        )
