"""
WSGI config for zimbabwe_supermarket project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zimbabwe_supermarket.settings')

application = get_wsgi_application()
