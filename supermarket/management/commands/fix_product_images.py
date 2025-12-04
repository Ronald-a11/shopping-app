from django.core.management.base import BaseCommand
from supermarket.models import Product


class Command(BaseCommand):
    help = 'Fix product images with reliable URLs'

    def handle(self, *args, **options):
        # Update product images with reliable, working URLs
        product_updates = {
            'Fresh Tomatoes (1kg)': 'https://images.unsplash.com/photo-1546470427-5c0b0b0b0b0b?w=400&h=300&fit=crop&auto=format',
            'Onions (1kg)': 'https://images.unsplash.com/photo-1518977956812-cd3dbadaaf31?w=400&h=300&fit=crop&auto=format',
            'Green Cabbage (1 head)': 'https://images.unsplash.com/photo-1594282486552-0b2b0b0b0b0b?w=400&h=300&fit=crop&auto=format',
            'Carrots (1kg)': 'https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?w=400&h=300&fit=crop&auto=format',
            'Bananas (1 bunch)': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400&h=300&fit=crop&auto=format',
            'Beef Steak (1kg)': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop&auto=format',
            'Chicken Breast (1kg)': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop&auto=format',
            'Pork Chops (1kg)': 'https://images.unsplash.com/photo-1607623814075-e51df1bdc82f?w=400&h=300&fit=crop&auto=format',
            'Fresh Milk (1L)': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop&auto=format',
            'Cheddar Cheese (250g)': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400&h=300&fit=crop&auto=format',
            'Butter (250g)': 'https://images.unsplash.com/photo-1589985278026-fd3a0bb7dc6f?w=400&h=300&fit=crop&auto=format',
            'Maize Meal (2kg)': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop&auto=format',
            'Rice (2kg)': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop&auto=format',
            'Bread (1 loaf)': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop&auto=format',
            'Coca Cola (500ml)': 'https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=400&h=300&fit=crop&auto=format',
            'Orange Juice (1L)': 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400&h=300&fit=crop&auto=format',
            'Mango Juice (1L)': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop&auto=format',
            'Passion Fruit Juice (1L)': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop&auto=format',
            'Water (500ml)': 'https://images.unsplash.com/photo-1548839140-5c7d3a0b0b0b?w=400&h=300&fit=crop&auto=format',
            'Potato Chips (150g)': 'https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400&h=300&fit=crop&auto=format',
            'Chocolate Bar (100g)': 'https://images.unsplash.com/photo-1511381939415-e44015466834?w=400&h=300&fit=crop&auto=format',
            'Dish Soap (500ml)': 'https://images.unsplash.com/photo-1581578731548-c6a0c3f2f4c4?w=400&h=300&fit=crop&auto=format',
            'Toilet Paper (4 rolls)': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=300&fit=crop&auto=format',
            'Toothpaste (100g)': 'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400&h=300&fit=crop&auto=format',
            'Shampoo (400ml)': 'https://images.unsplash.com/photo-1556228720-195a672e8a03?w=400&h=300&fit=crop&auto=format',
        }

        updated_count = 0
        for product_name, new_image_url in product_updates.items():
            try:
                product = Product.objects.get(name=product_name)
                product.image = new_image_url
                product.save()
                updated_count += 1
                self.stdout.write(f'Updated image for: {product_name}')
            except Product.DoesNotExist:
                self.stdout.write(f'Product not found: {product_name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} product images!')
        )



