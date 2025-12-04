from django.core.management.base import BaseCommand
from supermarket.models import Category, Product


class Command(BaseCommand):
    help = 'Populate the database with sample data'

    def handle(self, *args, **options):
        # Create categories
        categories_data = [
            {'name': 'Fresh Produce', 'description': 'Fresh fruits and vegetables from local farms'},
            {'name': 'Meat & Poultry', 'description': 'Fresh meat, chicken, and other poultry products'},
            {'name': 'Dairy & Eggs', 'description': 'Milk, cheese, yogurt, and fresh eggs'},
            {'name': 'Bakery', 'description': 'Fresh bread, pastries, and baked goods'},
            {'name': 'Pantry Staples', 'description': 'Rice, flour, cooking oil, and other essentials'},
            {'name': 'Beverages', 'description': 'Soft drinks, juices, water, and other beverages'},
            {'name': 'Snacks', 'description': 'Chips, nuts, cookies, and other snack items'},
            {'name': 'Household', 'description': 'Cleaning supplies, toiletries, and household items'},
        ]

        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create products
        products_data = [
            # Fresh Produce
            {'name': 'Fresh Tomatoes', 'description': 'Ripe, red tomatoes from local farms', 'category': 'Fresh Produce', 'price': 2.50, 'is_local_product': True, 'supplier': 'Harare Farm Co.'},
            {'name': 'Green Bananas', 'description': 'Fresh green bananas, perfect for cooking', 'category': 'Fresh Produce', 'price': 3.00, 'is_local_product': True, 'supplier': 'Mashonaland Farms'},
            {'name': 'Fresh Spinach', 'description': 'Organic spinach leaves, rich in iron', 'category': 'Fresh Produce', 'price': 1.50, 'is_local_product': True, 'supplier': 'Local Organic Farm'},
            {'name': 'Sweet Potatoes', 'description': 'Fresh sweet potatoes, great for roasting', 'category': 'Fresh Produce', 'price': 2.00, 'is_local_product': True, 'supplier': 'Zimbabwe Agriculture'},
            
            # Meat & Poultry
            {'name': 'Fresh Chicken Breast', 'description': 'Premium chicken breast, perfect for grilling', 'category': 'Meat & Poultry', 'price': 8.50, 'is_local_product': True, 'supplier': 'Zimbabwe Poultry Ltd'},
            {'name': 'Beef Mince', 'description': 'Fresh ground beef, ideal for burgers and pasta', 'category': 'Meat & Poultry', 'price': 12.00, 'is_local_product': True, 'supplier': 'Local Butcher Shop'},
            {'name': 'Fresh Fish (Tilapia)', 'description': 'Fresh tilapia fish from local lakes', 'category': 'Meat & Poultry', 'price': 15.00, 'is_local_product': True, 'supplier': 'Lake Kariba Fisheries'},
            
            # Dairy & Eggs
            {'name': 'Fresh Milk (1L)', 'description': 'Fresh whole milk from local dairy farms', 'category': 'Dairy & Eggs', 'price': 2.50, 'is_local_product': True, 'supplier': 'Zimbabwe Dairy Co.'},
            {'name': 'Free Range Eggs (12 pack)', 'description': 'Fresh eggs from free-range chickens', 'category': 'Dairy & Eggs', 'price': 4.00, 'is_local_product': True, 'supplier': 'Rural Poultry Farm'},
            {'name': 'Cheddar Cheese', 'description': 'Aged cheddar cheese, perfect for sandwiches', 'category': 'Dairy & Eggs', 'price': 6.50, 'is_local_product': False, 'supplier': 'International Foods'},
            
            # Bakery
            {'name': 'Fresh Bread Loaf', 'description': 'Freshly baked white bread, made daily', 'category': 'Bakery', 'price': 1.50, 'is_local_product': True, 'supplier': 'Harare Bakery'},
            {'name': 'Maize Meal Bread', 'description': 'Traditional maize meal bread', 'category': 'Bakery', 'price': 2.00, 'is_local_product': True, 'supplier': 'Traditional Bakery'},
            {'name': 'Croissants (6 pack)', 'description': 'Buttery croissants, perfect for breakfast', 'category': 'Bakery', 'price': 5.00, 'is_local_product': False, 'supplier': 'European Bakery'},
            
            # Pantry Staples
            {'name': 'Rice (5kg)', 'description': 'Long grain rice, perfect for everyday cooking', 'category': 'Pantry Staples', 'price': 8.00, 'is_local_product': False, 'supplier': 'Grain Importers'},
            {'name': 'Cooking Oil (1L)', 'description': 'Sunflower cooking oil, ideal for frying', 'category': 'Pantry Staples', 'price': 3.50, 'is_local_product': False, 'supplier': 'Oil Distributors'},
            {'name': 'Maize Meal (2kg)', 'description': 'Fine maize meal, staple food in Zimbabwe', 'category': 'Pantry Staples', 'price': 4.50, 'is_local_product': True, 'supplier': 'Local Millers'},
            
            # Beverages
            {'name': 'Coca Cola (2L)', 'description': 'Refreshing Coca Cola soft drink', 'category': 'Beverages', 'price': 2.50, 'is_local_product': False, 'supplier': 'Coca Cola Zimbabwe'},
            {'name': 'Fresh Orange Juice (1L)', 'description': 'Freshly squeezed orange juice', 'category': 'Beverages', 'price': 4.00, 'is_local_product': True, 'supplier': 'Citrus Farms'},
            {'name': 'Bottled Water (6 pack)', 'description': 'Pure drinking water, 500ml bottles', 'category': 'Beverages', 'price': 3.00, 'is_local_product': True, 'supplier': 'Zimbabwe Water Co.'},
            
            # Snacks
            {'name': 'Potato Chips', 'description': 'Crispy potato chips, salted flavor', 'category': 'Snacks', 'price': 2.00, 'is_local_product': False, 'supplier': 'Snack Distributors'},
            {'name': 'Peanuts (500g)', 'description': 'Roasted peanuts, perfect for snacking', 'category': 'Snacks', 'price': 3.50, 'is_local_product': True, 'supplier': 'Local Nut Farm'},
            {'name': 'Biscuits (Pack of 10)', 'description': 'Sweet biscuits, great with tea', 'category': 'Snacks', 'price': 2.50, 'is_local_product': False, 'supplier': 'Biscuit Company'},
            
            # Household
            {'name': 'Laundry Detergent (2L)', 'description': 'Powerful laundry detergent for all fabrics', 'category': 'Household', 'price': 8.50, 'is_local_product': False, 'supplier': 'Cleaning Products Ltd'},
            {'name': 'Toilet Paper (12 rolls)', 'description': 'Soft toilet paper, 2-ply', 'category': 'Household', 'price': 6.00, 'is_local_product': False, 'supplier': 'Paper Products'},
            {'name': 'Soap Bar (6 pack)', 'description': 'Gentle soap bars for personal hygiene', 'category': 'Household', 'price': 4.50, 'is_local_product': True, 'supplier': 'Local Soap Maker'},
        ]

        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults={
                    'description': product_data['description'],
                    'category': categories[product_data['category']],
                    'price': product_data['price'],
                    'is_local_product': product_data['is_local_product'],
                    'supplier': product_data['supplier'],
                    'stock_quantity': 50,  # Default stock
                    'is_available': True,
                }
            )
            if created:
                self.stdout.write(f'Created product: {product.name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with sample data!')
        )
