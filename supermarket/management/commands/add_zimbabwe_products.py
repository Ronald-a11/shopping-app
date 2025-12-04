from django.core.management.base import BaseCommand
from supermarket.models import Product, Category
from decimal import Decimal


class Command(BaseCommand):
    help = 'Add Zimbabwe grocery products with correct images and prices'

    def handle(self, *args, **options):
        # Create categories if they don't exist
        categories_data = [
            {'name': 'Fruits & Vegetables', 'description': 'Fresh fruits and vegetables'},
            {'name': 'Meat & Poultry', 'description': 'Fresh meat and poultry products'},
            {'name': 'Dairy Products', 'description': 'Milk, cheese, and dairy items'},
            {'name': 'Grains & Cereals', 'description': 'Rice, maize meal, and cereals'},
            {'name': 'Beverages', 'description': 'Soft drinks, juices, and water'},
            {'name': 'Snacks & Confectionery', 'description': 'Chips, sweets, and snacks'},
            {'name': 'Household Items', 'description': 'Cleaning supplies and household goods'},
            {'name': 'Personal Care', 'description': 'Toiletries and personal hygiene products'},
        ]
        
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Zimbabwe grocery products with realistic prices (in USD)
        products_data = [
            # Fruits & Vegetables
            {
                'name': 'Fresh Tomatoes (1kg)',
                'description': 'Fresh red tomatoes, perfect for cooking and salads',
                'category': 'Fruits & Vegetables',
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1546470427-5c0b0b0b0b0b?w=400',
                'stock_quantity': 50,
                'is_local_product': True,
                'supplier': 'Local Farm'
            },
            {
                'name': 'Onions (1kg)',
                'description': 'Fresh white onions, essential for cooking',
                'category': 'Fruits & Vegetables',
                'price': Decimal('1.80'),
                'image': 'https://images.unsplash.com/photo-1518977956812-cd3dbadaaf31?w=400',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Local Farm'
            },
            {
                'name': 'Green Cabbage (1 head)',
                'description': 'Fresh green cabbage, great for salads and cooking',
                'category': 'Fruits & Vegetables',
                'price': Decimal('1.20'),
                'image': 'https://images.unsplash.com/photo-1594282486552-0b2b0b0b0b0b?w=400',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Local Farm'
            },
            {
                'name': 'Carrots (1kg)',
                'description': 'Fresh orange carrots, rich in vitamins',
                'category': 'Fruits & Vegetables',
                'price': Decimal('2.00'),
                'image': 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=400',
                'stock_quantity': 40,
                'is_local_product': True,
                'supplier': 'Local Farm'
            },
            {
                'name': 'Bananas (1 bunch)',
                'description': 'Fresh yellow bananas, perfect for snacking',
                'category': 'Fruits & Vegetables',
                'price': Decimal('1.50'),
                'image': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Local Farm'
            },

            # Meat & Poultry
            {
                'name': 'Beef Steak (1kg)',
                'description': 'Fresh beef steak, perfect for grilling',
                'category': 'Meat & Poultry',
                'price': Decimal('8.50'),
                'image': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400',
                'stock_quantity': 15,
                'is_local_product': True,
                'supplier': 'Local Butcher'
            },
            {
                'name': 'Chicken Breast (1kg)',
                'description': 'Fresh chicken breast, lean and healthy',
                'category': 'Meat & Poultry',
                'price': Decimal('6.00'),
                'image': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Local Poultry Farm'
            },
            {
                'name': 'Pork Chops (1kg)',
                'description': 'Fresh pork chops, great for grilling',
                'category': 'Meat & Poultry',
                'price': Decimal('7.00'),
                'image': 'https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=400',
                'stock_quantity': 12,
                'is_local_product': True,
                'supplier': 'Local Butcher'
            },

            # Dairy Products
            {
                'name': 'Fresh Milk (1L)',
                'description': 'Fresh cow milk, pasteurized and safe',
                'category': 'Dairy Products',
                'price': Decimal('1.20'),
                'image': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Local Dairy Farm'
            },
            {
                'name': 'Cheddar Cheese (250g)',
                'description': 'Aged cheddar cheese, perfect for sandwiches',
                'category': 'Dairy Products',
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400',
                'stock_quantity': 25,
                'is_local_product': False,
                'supplier': 'Dairy Products Ltd'
            },
            {
                'name': 'Butter (250g)',
                'description': 'Fresh butter, great for cooking and baking',
                'category': 'Dairy Products',
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1589985278026-fd3a0bb7dc6f?w=400',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Local Dairy Farm'
            },

            # Grains & Cereals
            {
                'name': 'Maize Meal (2kg)',
                'description': 'Fine white maize meal, staple food in Zimbabwe',
                'category': 'Grains & Cereals',
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400',
                'stock_quantity': 50,
                'is_local_product': True,
                'supplier': 'Local Mill'
            },
            {
                'name': 'Rice (2kg)',
                'description': 'Long grain white rice, perfect for meals',
                'category': 'Grains & Cereals',
                'price': Decimal('3.20'),
                'image': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400',
                'stock_quantity': 40,
                'is_local_product': False,
                'supplier': 'Grain Importers'
            },
            {
                'name': 'Bread (1 loaf)',
                'description': 'Fresh white bread, baked daily',
                'category': 'Grains & Cereals',
                'price': Decimal('1.00'),
                'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400',
                'stock_quantity': 30,
                'is_local_product': True,
                'supplier': 'Local Bakery'
            },

            # Beverages
            {
                'name': 'Coca Cola (500ml)',
                'description': 'Classic Coca Cola soft drink',
                'category': 'Beverages',
                'price': Decimal('1.50'),
                'image': 'https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=400',
                'stock_quantity': 100,
                'is_local_product': False,
                'supplier': 'Coca Cola Zimbabwe'
            },
            {
                'name': 'Orange Juice (1L)',
                'description': 'Fresh orange juice, 100% pure',
                'category': 'Beverages',
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400&h=300&fit=crop',
                'stock_quantity': 25,
                'is_local_product': True,
                'supplier': 'Local Juice Company'
            },
            {
                'name': 'Mango Juice (1L)',
                'description': 'Fresh mango juice, tropical flavor',
                'category': 'Beverages',
                'price': Decimal('3.20'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 20,
                'is_local_product': True,
                'supplier': 'Local Juice Company'
            },
            {
                'name': 'Passion Fruit Juice (1L)',
                'description': 'Fresh passion fruit juice, exotic taste',
                'category': 'Beverages',
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop',
                'stock_quantity': 15,
                'is_local_product': True,
                'supplier': 'Local Juice Company'
            },
            {
                'name': 'Water (500ml)',
                'description': 'Pure drinking water, safe and clean',
                'category': 'Beverages',
                'price': Decimal('0.80'),
                'image': 'https://images.unsplash.com/photo-1548839140-5c7d3a0b0b0b?w=400&h=300&fit=crop',
                'stock_quantity': 80,
                'is_local_product': True,
                'supplier': 'Local Water Company'
            },

            # Snacks & Confectionery
            {
                'name': 'Potato Chips (150g)',
                'description': 'Crispy potato chips, salted flavor',
                'category': 'Snacks & Confectionery',
                'price': Decimal('2.20'),
                'image': 'https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400',
                'stock_quantity': 60,
                'is_local_product': False,
                'supplier': 'Snack Company'
            },
            {
                'name': 'Chocolate Bar (100g)',
                'description': 'Milk chocolate bar, sweet treat',
                'category': 'Snacks & Confectionery',
                'price': Decimal('1.80'),
                'image': 'https://images.unsplash.com/photo-1511381939415-e44015466834?w=400',
                'stock_quantity': 45,
                'is_local_product': False,
                'supplier': 'Confectionery Ltd'
            },

            # Household Items
            {
                'name': 'Dish Soap (500ml)',
                'description': 'Liquid dish soap, cuts through grease',
                'category': 'Household Items',
                'price': Decimal('2.50'),
                'image': 'https://images.unsplash.com/photo-1581578731548-c6a0c3f2f4c4?w=400',
                'stock_quantity': 35,
                'is_local_product': False,
                'supplier': 'Cleaning Products Co'
            },
            {
                'name': 'Toilet Paper (4 rolls)',
                'description': 'Soft toilet paper, 4-pack',
                'category': 'Household Items',
                'price': Decimal('3.50'),
                'image': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400',
                'stock_quantity': 40,
                'is_local_product': False,
                'supplier': 'Household Products Ltd'
            },

            # Personal Care
            {
                'name': 'Toothpaste (100g)',
                'description': 'Fluoride toothpaste, mint flavor',
                'category': 'Personal Care',
                'price': Decimal('2.80'),
                'image': 'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400',
                'stock_quantity': 30,
                'is_local_product': False,
                'supplier': 'Personal Care Co'
            },
            {
                'name': 'Shampoo (400ml)',
                'description': 'Moisturizing shampoo for all hair types',
                'category': 'Personal Care',
                'price': Decimal('4.50'),
                'image': 'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400',
                'stock_quantity': 25,
                'is_local_product': False,
                'supplier': 'Personal Care Co'
            },
        ]

        # Create products
        for product_data in products_data:
            category = Category.objects.get(name=product_data['category'])
            
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'category': category,
                    'price': product_data['price'],
                    'image': product_data['image'],
                    'stock_quantity': product_data['stock_quantity'],
                    'is_local_product': product_data['is_local_product'],
                    'supplier': product_data['supplier'],
                    'is_available': True
                }
            )
            
            if created:
                self.stdout.write(f'Created product: {product.name}')
            else:
                self.stdout.write(f'Product already exists: {product.name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully added Zimbabwe grocery products!')
        )
