# Zimbabwe Supermarket - Setup Instructions

## Quick Start

### Option 1: Using the Batch File (Windows)
1. Double-click `start.bat` to automatically install dependencies and start the server
2. Open your browser to http://127.0.0.1:8000

### Option 2: Manual Setup

1. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Database Migrations**
   ```bash
   python manage.py migrate
   ```

3. **Populate Sample Data**
   ```bash
   python manage.py populate_data
   ```

4. **Create Admin User (Optional)**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

6. **Access the Application**
   - Main site: http://127.0.0.1:8000
   - Admin panel: http://127.0.0.1:8000/admin

## Features Included

### 🛒 Shopping Features
- Product catalog with categories
- Shopping cart functionality
- Order management system
- User authentication
- Search and filtering

### 🇿🇼 Zimbabwe-Specific Features
- Local product highlighting
- Zimbabwe Dollar (ZWD) currency display
- Zimbabwean provinces in delivery form
- Local supplier information
- Community-focused messaging

### 🎨 User Interface
- Responsive design (mobile-friendly)
- Modern Bootstrap 5 styling
- Interactive JavaScript features
- Professional color scheme

### 🔧 Admin Features
- Product and category management
- Order tracking and management
- Customer message handling
- Inventory control

## Sample Data

The application comes with sample data including:
- 8 product categories
- 25+ sample products
- Mix of local and imported products
- Realistic pricing in USD

## File Structure

```
zimbabwe-supermarket/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── start.bat                # Windows startup script
├── README.md                # Project documentation
├── SETUP_INSTRUCTIONS.md    # This file
├── zimbabwe_supermarket/    # Django project settings
├── supermarket/             # Main application
├── templates/               # HTML templates
└── static/                  # CSS and JavaScript files
```

## Troubleshooting

### Common Issues

1. **Django not found error**
   - Make sure you've installed the requirements: `pip install -r requirements.txt`

2. **Database errors**
   - Run migrations: `python manage.py migrate`

3. **Static files not loading**
   - Run: `python manage.py collectstatic`

4. **Port already in use**
   - Use a different port: `python manage.py runserver 8001`

### Getting Help

If you encounter any issues:
1. Check the console output for error messages
2. Ensure all dependencies are installed
3. Verify Python version (3.8+ recommended)
4. Check that all files are in the correct locations

## Next Steps

1. **Customize the Design**
   - Edit `static/css/style.css` for styling changes
   - Modify templates in `templates/supermarket/`

2. **Add Products**
   - Use the admin panel at `/admin/`
   - Or create a management command

3. **Configure for Production**
   - Update `settings.py` for production
   - Set up a proper database
   - Configure static file serving

4. **Add Payment Integration**
   - Integrate with local payment providers
   - Add mobile money support

## Support

For questions or issues:
- Check the README.md for detailed documentation
- Review the Django documentation
- Contact the development team

---

**Zimbabwe Supermarket** - Supporting local communities! 🇿🇼
