"""
WSGI configuration for deploying this project on PythonAnywhere.

This file is a TEMPLATE. Do not import it directly — PythonAnywhere does not
read it from the repository. Instead:

  1. Open the "Web" tab on PythonAnywhere.
  2. Click the link to the WSGI configuration file
     (/var/www/<username>_pythonanywhere_com_wsgi.py).
  3. Delete everything in that file and paste the contents of this one.
  4. Replace every occurrence of YOURUSERNAME with your PythonAnywhere
     username, and paste your real generated secret key where indicated.
  5. Click "Save", then "Reload" on the Web tab.

The secret key is set here rather than committed to the repository because
/var/www/ is private to your account, whereas the repository is public.
"""

import os
import sys

# --- Project location -------------------------------------------------------
# The directory containing manage.py, i.e. where you cloned the repository.
path = '/home/YOURUSERNAME/shopping-app'
if path not in sys.path:
    sys.path.insert(0, path)

# --- Settings ---------------------------------------------------------------
os.environ['DJANGO_SETTINGS_MODULE'] = 'zimbabwe_supermarket.settings'

# Paste the secret key generated for you. Never commit this value.
os.environ['DJANGO_SECRET_KEY'] = 'PASTE-YOUR-GENERATED-SECRET-KEY-HERE'

# Django refuses requests for any host not listed here.
os.environ['DJANGO_ALLOWED_HOSTS'] = 'YOURUSERNAME.pythonanywhere.com'

# Where `manage.py collectstatic` writes, and what the Web tab's static file
# mapping for /static/ must point at.
os.environ['DJANGO_STATIC_ROOT'] = '/home/YOURUSERNAME/shopping-app/staticfiles'

# DJANGO_DEBUG is deliberately NOT set: settings.py treats anything other than
# "1" as debug-off, which is what production wants.

# PythonAnywhere terminates HTTPS at its proxy and forwards X-Forwarded-Proto,
# which settings.py already trusts via SECURE_PROXY_SSL_HEADER, so the redirect
# to HTTPS is safe. If you ever see "too many redirects", set this to '0'.
os.environ['DJANGO_SECURE_SSL_REDIRECT'] = '1'

# --- Application ------------------------------------------------------------
from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
