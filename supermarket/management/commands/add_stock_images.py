from django.core.management.base import BaseCommand
from supermarket.models import Product, Category


class Command(BaseCommand):
    help = 'Add stock images to products and categories'

    def handle(self, *args, **options):
        # Stock images URLs for different product categories
        stock_images = {
            'Fresh Produce': {
                'tomatoes': 'https://images.unsplash.com/photo-1546470427-5a2b8a4b8b8b?w=400&h=300&fit=crop',
                'bananas': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400&h=300&fit=crop',
                'spinach': 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400&h=300&fit=crop',
                'sweet_potatoes': 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=400&h=300&fit=crop',
            },
            'Meat & Poultry': {
                'chicken': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop',
                'beef': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop',
                'fish': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400&h=300&fit=crop',
            },
            'Dairy & Eggs': {
                'milk': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop',
                'eggs': 'https://images.unsplash.com/photo-1518569656558-1e25a3d0e1a4?w=400&h=300&fit=crop',
                'cheese': 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400&h=300&fit=crop',
            },
            'Bakery': {
                'bread': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop',
                'maize_bread': 'https://images.unsplash.com/photo-1586444248902-2f64eddc13df?w=400&h=300&fit=crop',
                'croissants': 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400&h=300&fit=crop',
            },
            'Pantry Staples': {
                'rice': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
                'cooking_oil': 'https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&h=300&fit=crop',
                'maize_meal': 'https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&h=300&fit=crop',
            },
            'Beverages': {
                'coca_cola': 'https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=400&h=300&fit=crop',
                'orange_juice': 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?w=400&h=300&fit=crop',
                'water': 'https://images.unsplash.com/photo-1548839140-5b7c4b7b7b7b?w=400&h=300&fit=crop',
            },
            'Snacks': {
                'chips': 'https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400&h=300&fit=crop',
                'peanuts': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=300&fit=crop',
                'biscuits': 'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400&h=300&fit=crop',
            },
            'Household': {
                'detergent': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=300&fit=crop',
                'toilet_paper': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=300&fit=crop',
                'soap': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=400&h=300&fit=crop',
            }
        }

        # Category images
        category_images = {
            'Fresh Produce': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&h=300&fit=crop',
            'Meat & Poultry': 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop',
            'Dairy & Eggs': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop',
            'Bakery': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop',
            'Pantry Staples': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop',
            'Beverages': 'https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=400&h=300&fit=crop',
            'Snacks': 'https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400&h=300&fit=crop',
            'Household': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=300&fit=crop',
        }

        # Update categories with images
        for category_name, image_url in category_images.items():
            try:
                category = Category.objects.get(name=category_name)
                category.image = image_url
                category.save()
                self.stdout.write(f'Updated category: {category_name}')
            except Category.DoesNotExist:
                self.stdout.write(f'Category not found: {category_name}')

        # Update products with images
        for product in Product.objects.all():
            category_name = product.category.name
            product_name_lower = product.name.lower()
            
            # Find matching image based on product name keywords
            image_url = None
            if category_name in stock_images:
                category_images_dict = stock_images[category_name]
                
                # Try to match product name with image keys
                for key, url in category_images_dict.items():
                    if any(keyword in product_name_lower for keyword in key.split('_')):
                        image_url = url
                        break
                
                # If no specific match, use the first image from the category
                if not image_url and category_images_dict:
                    image_url = list(category_images_dict.values())[0]
            
            if image_url:
                product.image = image_url
                product.save()
                self.stdout.write(f'Updated product: {product.name}')
            else:
                # Use a default image
                product.image = 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=400&h=300&fit=crop'
                product.save()
                self.stdout.write(f'Updated product with default image: {product.name}')

        self.stdout.write(
            self.style.SUCCESS('Successfully added stock images to all products and categories!')
        )

