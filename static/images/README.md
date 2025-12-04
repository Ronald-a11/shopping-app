# Zimbabwe Supermarket - Stock Images

This directory contains references to stock images used in the Zimbabwe Supermarket application.

## Image Sources

All images are sourced from [Unsplash](https://unsplash.com/), which provides free, high-quality stock photos.

## Image Categories

### Hero Images
- **Main Hero**: Shopping scene for homepage
- **About Hero**: Business/team image for about page

### Category Images
- **Fresh Produce**: Fruits and vegetables
- **Meat & Poultry**: Meat products and chicken
- **Dairy & Eggs**: Milk, cheese, and eggs
- **Bakery**: Bread and baked goods
- **Pantry Staples**: Rice, flour, and cooking essentials
- **Beverages**: Soft drinks, juices, and water
- **Snacks**: Chips, nuts, and cookies
- **Household**: Cleaning supplies and toiletries

### Product Images
Each product has been assigned an appropriate image based on its category and name. Images are loaded dynamically from Unsplash URLs.

## Usage

Images are loaded directly from Unsplash URLs in the templates. This approach:
- Reduces server storage requirements
- Ensures high-quality images
- Provides automatic optimization
- Maintains fast loading times

## Customization

To use your own images:
1. Replace the Unsplash URLs in the database
2. Upload images to the `static/images/` directory
3. Update the image field references in templates

## License

All images from Unsplash are free to use under the Unsplash License.
