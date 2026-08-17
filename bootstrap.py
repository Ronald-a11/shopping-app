#!/usr/bin/env python
"""
Setup script for Zimbabwe Supermarket
Run this script to set up the project for the first time
"""

import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def setup_django():
    """Set up Django project"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zimbabwe_supermarket.settings')
    django.setup()

def main():
    """Main setup function"""
    print("🇿🇼 Setting up Zimbabwe Supermarket...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Install requirements
    if not run_command('pip install -r requirements.txt', 'Installing Python dependencies'):
        print("❌ Failed to install dependencies. Please check your Python environment.")
        sys.exit(1)
    
    # Set up Django
    setup_django()
    
    # Run migrations
    if not run_command('python manage.py migrate', 'Running database migrations'):
        print("❌ Failed to run migrations")
        sys.exit(1)
    
    # Create superuser (optional)
    print("\n🔐 Creating superuser account...")
    print("You can skip this step by pressing Ctrl+C")
    try:
        execute_from_command_line(['manage.py', 'createsuperuser'])
    except KeyboardInterrupt:
        print("⏭️  Skipped superuser creation")
    except Exception as e:
        print(f"⚠️  Superuser creation failed: {e}")
    
    # Populate sample data
    print("\n📦 Populating database with sample data...")
    try:
        execute_from_command_line(['manage.py', 'populate_data'])
        print("✅ Sample data added successfully")
    except Exception as e:
        print(f"⚠️  Failed to populate sample data: {e}")
    
    # Collect static files
    if not run_command('python manage.py collectstatic --noinput', 'Collecting static files'):
        print("⚠️  Failed to collect static files")
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run the development server: python manage.py runserver")
    print("2. Open your browser to: http://127.0.0.1:8000")
    print("3. Access admin panel: http://127.0.0.1:8000/admin")
    print("\n🇿🇼 Welcome to Zimbabwe Supermarket!")

if __name__ == '__main__':
    main()
