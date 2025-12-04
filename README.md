# Zimbabwe Supermarket - Online Shopping Platform

A comprehensive e-commerce platform designed specifically for Zimbabwe, featuring local products, Zimbabwean currency support, and community-focused shopping experience.

## Features

### 🛒 Core Shopping Features
- **Product Catalog**: Browse products by category with advanced filtering
- **Shopping Cart**: Add, update, and remove items with real-time updates
- **Order Management**: Complete checkout process with order tracking
- **User Accounts**: Secure user registration and authentication
- **Search Functionality**: Find products quickly with intelligent search

### 🇿🇼 Zimbabwe-Specific Features
- **Local Products**: Special highlighting for Zimbabwean-made products
- **Currency Display**: Prices shown in both USD and Zimbabwe Dollars (ZWD)
- **Zimbabwean Provinces**: Delivery address form includes all Zimbabwe provinces
- **Local Suppliers**: Product information includes local supplier details
- **Community Focus**: Emphasis on supporting local farmers and businesses

### 🎨 User Experience
- **Responsive Design**: Mobile-first design that works on all devices
- **Modern UI**: Clean, intuitive interface with Bootstrap 5
- **Fast Loading**: Optimized for quick page loads
- **Accessibility**: Built with accessibility best practices

### 🔧 Admin Features
- **Product Management**: Add, edit, and manage products and categories
- **Order Management**: Track and update order status
- **Inventory Control**: Monitor stock levels and availability
- **Customer Support**: Manage customer inquiries and messages

## Technology Stack

- **Backend**: Django 4.2.7 (Python)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5.3.0
- **Icons**: Font Awesome 6.0.0
- **Database**: SQLite (development) / PostgreSQL (production)
- **Image Handling**: Pillow for image processing

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd zimbabwe-supermarket
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser account**
   ```bash
   python manage.py createsuperuser
   ```

6. **Populate with sample data (optional)**
   ```bash
   python manage.py populate_data
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/

## Project Structure

```
zimbabwe-supermarket/
├── manage.py
├── requirements.txt
├── README.md
├── zimbabwe_supermarket/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── supermarket/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── urls.py
│   └── management/
│       └── commands/
│           └── populate_data.py
├── templates/
│   ├── base.html
│   └── supermarket/
│       ├── home.html
│       ├── product_list.html
│       ├── product_detail.html
│       ├── cart.html
│       ├── checkout.html
│       ├── order_detail.html
│       ├── order_history.html
│       ├── contact.html
│       └── about.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## Key Features Explained

### Shopping Cart System
- Session-based cart for anonymous users
- User-specific cart for authenticated users
- Real-time cart updates without page refresh
- Persistent cart across browser sessions

### Order Management
- Complete order lifecycle tracking
- Status updates (Pending → Processing → Shipped → Delivered)
- Order history for users
- Delivery information management

### Local Product Support
- Special badges for Zimbabwean products
- Supplier information display
- Local product filtering
- Community support messaging

### Currency Support
- Dual currency display (USD/ZWD)
- Automatic conversion rates
- Localized pricing format

## Customization

### Adding New Product Categories
1. Access the admin panel
2. Navigate to Categories
3. Add new category with name and description
4. Upload category image (optional)

### Managing Products
1. Go to Products in admin panel
2. Add new products with:
   - Name and description
   - Category assignment
   - Price in USD
   - Stock quantity
   - Local product flag
   - Supplier information
   - Product images

### Styling Customization
- Modify `static/css/style.css` for custom styling
- Update color scheme in CSS variables
- Add custom animations and effects

## Deployment

### Production Settings
1. Update `settings.py` for production:
   - Set `DEBUG = False`
   - Configure proper database
   - Set up static file serving
   - Configure email settings

2. Set up web server (Nginx/Apache)
3. Configure WSGI server (Gunicorn)
4. Set up SSL certificate
5. Configure domain and DNS

### Environment Variables
Create a `.env` file for sensitive settings:
```
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=your-database-url
EMAIL_HOST=your-email-host
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Email: support@zimbabwesupermarket.co.zw
- Phone: +263 4 XXX XXXX
- Address: 123 Samora Machel Avenue, Harare, Zimbabwe

## Acknowledgments

- Local farmers and suppliers in Zimbabwe
- Django community for the excellent framework
- Bootstrap team for the UI components
- Font Awesome for the icons

---

**Zimbabwe Supermarket** - Supporting local communities, one purchase at a time. 🇿🇼
