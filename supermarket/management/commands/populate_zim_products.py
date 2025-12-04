from django.core.management.base import BaseCommand
from supermarket.models import Category, Product
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate database with Zimbabwe supermarket products'

    def handle(self, *args, **options):
        # Create categories
        categories_data = [
            {
                'name': 'Fresh Produce',
                'description': 'Fresh fruits and vegetables from local farms',
                'image': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&h=300&fit=crop'
            },
            {
                'name': 'Meat & Poultry',
                'description': 'Fresh meat and poultry products',
                'image': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop'
            },
            {
                'name': 'Dairy & Eggs',
                'description': 'Fresh dairy products and eggs',
                'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop'
            },
            {
                'name': 'Bakery',
                'description': 'Fresh bread, pastries, and baked goods',
                'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop'
            },
            {
                'name': 'Pantry Staples',
                'description': 'Rice, maize meal, cooking oil, and other essentials',
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop'
            },
            {
                'name': 'Beverages',
                'description': 'Soft drinks, juices, and other beverages',
                'image': 'https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400&h=300&fit=crop'
            },
            {
                'name': 'Snacks & Confectionery',
                'description': 'Chips, sweets, and snack foods',
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop'
            },
            {
                'name': 'Household Items',
                'description': 'Cleaning supplies and household essentials',
                'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop'
            }
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create products
        products_data = [
            # Fresh Produce
            {
                'name': 'Fresh Tomatoes (1kg)',
                'description': 'Fresh, locally grown tomatoes perfect for cooking and salads',
                'category': 'Fresh Produce',
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1546470427-5c4b0a0a0b0b?w=400&h=300&fit=crop',
                'stock_quantity': 50,
                'is_local_product': True,
                'supplier': 'Harare Fresh Farms'
            },
            {
                'name': 'Green Bananas (1 bunch)',
                'description': 'Fresh green bananas, perfect for cooking',
                'category': 'Fresh Produce',
                'price': Decimal('3.00'),
                'image': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Mashonaland Farms'
            },
            {
                'name': 'Onions (1kg)',
                'description': 'Fresh red onions, essential for cooking',
                'category': 'Fresh Produce',
                'price': Decimal('1.80'),
                'image': 'https://images.unsplash.com/photo-1518977956812-cd3dbadaaf31?w=400&h=300&fit=crop',
                'stock_quantity': 40,
                'is_local_product': True,
                'supplier': 'Zimbabwe Onion Co.'
            },
            {
                'name': 'Cabbage (1 head)',
                'description': 'Fresh green cabbage, perfect for salads and cooking',
                'category': 'Fresh Produce',
                'price': Decimal('2.20'),
                'image': 'https://images.unsplash.com/photo-1594282486552-afeb8a0a0b0b?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Local Vegetable Growers'
            },

            # Meat & Poultry
            {
                'name': 'Beef Steak (500g)',
                'description': 'Premium beef steak, perfect for grilling',
                'category': 'Meat & Poultry',
                'price': Decimal('8.50'),
                'image': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Zimbabwe Beef Co.'
            },
            {
                'name': 'Chicken Breast (1kg)',
                'description': 'Fresh chicken breast, skinless and boneless',
                'category': 'Meat & Poultry',
                'price': Decimal('6.00'),
                'image': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop',
                'stock_quantity': 35,
                'is_local_product': True,
                'supplier': 'Zimbabwe Poultry Ltd'
            },
            {
                'name': 'Pork Chops (500g)',
                'description': 'Fresh pork chops, perfect for grilling or frying',
                'category': 'Meat & Poultry',
                'price': Decimal('5.50'),
                'image': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop',
                'stock_quantity': 15,
                'is_local_product': True,
                'supplier': 'Local Pork Farm'
            },

            # Dairy & Eggs
            {
                'name': 'Fresh Milk (1L)',
                'description': 'Fresh whole milk from local dairy farms',
                'category': 'Dairy & Eggs',
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop',
                'stock_quantity': 60,
                'is_local_product': True,
                'supplier': 'Zimbabwe Dairy Co.'
            },
            {
                'name': 'Free Range Eggs (12 pack)',
                'description': 'Fresh free-range eggs from local farms',
                'category': 'Dairy & Eggs',
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1518569656558-1f25e69d93d3?w=400&h=300&fit=crop',
                'stock_quantity': 45,
                'is_local_product': True,
                'supplier': 'Mashonaland Poultry'
            },
            {
                'name': 'Cheddar Cheese (250g)',
                'description': 'Aged cheddar cheese, perfect for cooking and snacking',
                'category': 'Dairy & Eggs',
                'price': Decimal('4.20'),
                'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': False,
                'supplier': 'Imported'
            },

            # Bakery
            {
                'name': 'Fresh White Bread (1 loaf)',
                'description': 'Freshly baked white bread, perfect for breakfast',
                'category': 'Bakery',
                'price': Decimal('1.50'),
                'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Harare Bakery'
            },
            {
                'name': 'Brown Bread (1 loaf)',
                'description': 'Freshly baked brown bread, healthier option',
                'category': 'Bakery',
                'price': Decimal('1.80'),
                'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Harare Bakery'
            },
            {
                'name': 'Maize Meal (2kg)',
                'description': 'Fine maize meal, staple food in Zimbabwe',
                'category': 'Bakery',
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 40,
                'is_local_product': True,
                'supplier': 'Zimbabwe Grain Co.'
            },

            # Pantry Staples
            {
                'name': 'Rice (2kg)',
                'description': 'Long grain white rice, perfect for everyday cooking',
                'category': 'Pantry Staples',
                'price': Decimal('4.50'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 35,
                'is_local_product': False,
                'supplier': 'Imported'
            },
            {
                'name': 'Cooking Oil (1L)',
                'description': 'Vegetable cooking oil, essential for cooking',
                'category': 'Pantry Staples',
                'price': Decimal('3.20'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 50,
                'is_local_product': False,
                'supplier': 'Imported'
            },
            {
                'name': 'Salt (500g)',
                'description': 'Table salt, essential seasoning',
                'category': 'Pantry Staples',
                'price': Decimal('0.80'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 60,
                'is_local_product': False,
                'supplier': 'Imported'
            },
            {
                'name': 'Sugar (1kg)',
                'description': 'White granulated sugar',
                'category': 'Pantry Staples',
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'stock_quantity': 40,
                'is_local_product': False,
                'supplier': 'Imported'
            },

            # Beverages
            {
                'name': 'Coca Cola (2L)',
                'description': 'Classic Coca Cola soft drink',
                'category': 'Beverages',
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1544145945-f90425340c7e?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': False,
                'supplier': 'Coca Cola Zimbabwe'
            },
            {
                'name': 'Orange Juice (1L)',
                'description': 'Fresh orange juice, no added sugar',
                'category': 'Beverages',
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1613478223719-4ab8038ded72?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Zimbabwe Juice Co.'
            },
            {
                'name': 'Water (1.5L)',
                'description': 'Pure drinking water',
                'category': 'Beverages',
                'price': Decimal('1.20'),
                'image': 'https://images.unsplash.com/photo-1548839140-5c4b7c7b7b7b?w=400&h=300&fit=crop',
                'stock_quantity': 80,
                'is_local_product': True,
                'supplier': 'Zimbabwe Water Co.'
            },

            # Snacks & Confectionery
            {
                'name': 'Potato Chips (150g)',
                'description': 'Crispy potato chips, salted flavor',
                'category': 'Snacks & Confectionery',
                'price': Decimal('2.00'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 35,
                'is_local_product': False,
                'supplier': 'Imported'
            },
            {
                'name': 'Chocolate Bar (100g)',
                'description': 'Milk chocolate bar',
                'category': 'Snacks & Confectionery',
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 40,
                'is_local_product': False,
                'supplier': 'Imported'
            },

            # Household Items
            {
                'name': 'Dish Soap (500ml)',
                'description': 'Liquid dish soap, effective cleaning',
                'category': 'Household Items',
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop',
                'stock_quantity': 30,
                'is_local_product': False,
                'supplier': 'Imported'
            },
            {
                'name': 'Toilet Paper (4 pack)',
                'description': 'Soft toilet paper, 4 rolls',
                'category': 'Household Items',
                'price': Decimal('4.50'),
                'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': False,
                'supplier': 'Imported'
            },
            {
                'name': 'Laundry Detergent (2kg)',
                'description': 'Powder laundry detergent, effective cleaning',
                'category': 'Household Items',
                'price': Decimal('6.50'),
                'image': 'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': False,
                'supplier': 'Imported'
            }
        ]

        for product_data in products_data:
            category = categories[product_data['category']]
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'category': category,
                    'price': product_data['price'],
                    'image': product_data['image'],
                    'stock_quantity': product_data['stock_quantity'],
                    'is_available': True,
                    'is_local_product': product_data['is_local_product'],
                    'supplier': product_data['supplier']
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with Zimbabwe supermarket products!')
        )
