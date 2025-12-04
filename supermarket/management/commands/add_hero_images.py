from django.core.management.base import BaseCommand
import os


class Command(BaseCommand):
    help = 'Add hero images and other missing images'

    def handle(self, *args, **options):
        # Create static/images directory if it doesn't exist
        static_images_dir = 'static/images'
        os.makedirs(static_images_dir, exist_ok=True)
        
        # Hero images URLs
        hero_images = {
            'hero-shopping.jpg': 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800&h=600&fit=crop',
            'about-hero.jpg': 'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop',
        }
        
        # Create a simple HTML file to display the images
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Stock Images</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .image-container { margin: 20px 0; }
        img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px; }
        h2 { color: #28a745; }
    </style>
</head>
<body>
    <h1>Zimbabwe Supermarket - Stock Images</h1>
    <p>These are the stock images being used in the application:</p>
    
    <h2>Hero Images</h2>
    <div class="image-container">
        <h3>Main Hero Image</h3>
        <img src="https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800&h=600&fit=crop" alt="Shopping Hero">
    </div>
    
    <div class="image-container">
        <h3>About Hero Image</h3>
        <img src="https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800&h=600&fit=crop" alt="About Hero">
    </div>
    
    <h2>Product Category Images</h2>
    <div class="image-container">
        <h3>Fresh Produce</h3>
        <img src="https://images.unsplash.com/photo-1542838132-92c53300491e?w=400&h=300&fit=crop" alt="Fresh Produce">
    </div>
    
    <div class="image-container">
        <h3>Meat & Poultry</h3>
        <img src="https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop" alt="Meat & Poultry">
    </div>
    
    <div class="image-container">
        <h3>Dairy & Eggs</h3>
        <img src="https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop" alt="Dairy & Eggs">
    </div>
    
    <div class="image-container">
        <h3>Bakery</h3>
        <img src="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop" alt="Bakery">
    </div>
    
    <div class="image-container">
        <h3>Pantry Staples</h3>
        <img src="https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&h=300&fit=crop" alt="Pantry Staples">
    </div>
    
    <div class="image-container">
        <h3>Beverages</h3>
        <img src="https://images.unsplash.com/photo-1581636625402-29b2a704ef13?w=400&h=300&fit=crop" alt="Beverages">
    </div>
    
    <div class="image-container">
        <h3>Snacks</h3>
        <img src="https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400&h=300&fit=crop" alt="Snacks">
    </div>
    
    <div class="image-container">
        <h3>Household</h3>
        <img src="https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=300&fit=crop" alt="Household">
    </div>
    
    <h2>Sample Product Images</h2>
    <div class="image-container">
        <h3>Fresh Tomatoes</h3>
        <img src="https://images.unsplash.com/photo-1546470427-5a2b8a4b8b8b?w=400&h=300&fit=crop" alt="Fresh Tomatoes">
    </div>
    
    <div class="image-container">
        <h3>Green Bananas</h3>
        <img src="https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400&h=300&fit=crop" alt="Green Bananas">
    </div>
    
    <div class="image-container">
        <h3>Fresh Chicken Breast</h3>
        <img src="https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400&h=300&fit=crop" alt="Fresh Chicken Breast">
    </div>
    
    <div class="image-container">
        <h3>Fresh Milk</h3>
        <img src="https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400&h=300&fit=crop" alt="Fresh Milk">
    </div>
    
    <div class="image-container">
        <h3>Fresh Bread</h3>
        <img src="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&h=300&fit=crop" alt="Fresh Bread">
    </div>
    
    <p><strong>Note:</strong> All images are sourced from Unsplash and are free to use. They are loaded dynamically from the URLs above.</p>
</body>
</html>
        """
        
        # Write the HTML file
        with open('static/images/stock_images.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created stock images reference!')
        )
        self.stdout.write('You can view all stock images at: static/images/stock_images.html')
