"""WSGI entry point for a PythonAnywhere web app.

`deploy/pythonanywhere_setup.sh` copies this over the file the Web tab points at
(/var/www/<username>_pythonanywhere_com_wsgi.py); after that, press **Reload**.

Per-site settings — the secret key and the site's hostname — are read from
`~/.jkc_env`, which the setup script writes. Keeping them outside the
repository means the secret key is never committed, and pulling new code can
never overwrite it.
"""
import os
import sys
from pathlib import Path

# The defaults match the setup script. The environment variables are here so
# this file can be pointed at a checkout somewhere else (and so it can be
# tested off PythonAnywhere).
PROJECT_DIR = Path(os.environ.get('JKC_PROJECT_DIR', Path.home() / 'shopping-app'))
ENV_FILE = Path(os.environ.get('JKC_ENV_FILE', Path.home() / '.jkc_env'))

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        # setdefault: a variable already set in the environment wins, which is
        # what lets a console session override one for a one-off command.
        os.environ.setdefault(key.strip(), value.strip())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zimbabwe_supermarket.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402  (needs the path above)

application = get_wsgi_application()
