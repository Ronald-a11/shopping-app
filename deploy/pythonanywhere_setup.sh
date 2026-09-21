#!/usr/bin/env bash
#
# Set up — or update — JKC Supermarket on PythonAnywhere.
#
# First time, in a PythonAnywhere Bash console:
#
#   git clone https://github.com/Ronald-a11/shopping-app.git ~/shopping-app
#   bash ~/shopping-app/deploy/pythonanywhere_setup.sh
#
# To deploy later changes, run the same script again: it pulls the new code,
# installs anything new, migrates the database, refreshes the static files and
# updates the WSGI file. Then press Reload on the Web tab.
#
set -euo pipefail

PROJECT_DIR="$HOME/shopping-app"
VENV_DIR="$HOME/.virtualenvs/jkc"
ENV_FILE="$HOME/.jkc_env"
USERNAME="$(whoami)"
DOMAIN="${USERNAME}.pythonanywhere.com"
WSGI_FILE="/var/www/${USERNAME}_pythonanywhere_com_wsgi.py"

say() { printf '\n==> %s\n' "$1"; }
run_py() { python "$@"; }

say "Code"
cd "$PROJECT_DIR"
git pull --ff-only
git log --oneline -1

say "Python and packages"
PYTHON=""
# Django 4.2 supports 3.10–3.12. Newest first, so a free account gets the best
# one it has.
for version in 3.12 3.11 3.10; do
    if command -v "python$version" >/dev/null 2>&1; then
        PYTHON="python$version"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "No supported Python found (needs 3.10, 3.11 or 3.12)." >&2
    exit 1
fi
echo "Using $PYTHON"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating the virtualenv at $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "Packages are up to date."

say "Site settings"
if [ ! -f "$ENV_FILE" ]; then
    SECRET_KEY="$(run_py -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
    cat > "$ENV_FILE" <<ENV
# Settings for the live site. Private: this file is NOT in the repository.
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_ALLOWED_HOSTS=$DOMAIN
# PythonAnywhere's "Force HTTPS" switch on the Web tab does the redirecting.
# Having Django redirect as well can loop, so it stays off here.
DJANGO_SECURE_SSL_REDIRECT=0
ENV
    chmod 600 "$ENV_FILE"
    echo "Wrote $ENV_FILE with a newly generated secret key."
else
    echo "$ENV_FILE already exists — keeping it (and its secret key)."
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
export DJANGO_SETTINGS_MODULE=zimbabwe_supermarket.settings

say "Database"
run_py manage.py migrate --noinput

say "Static files"
run_py manage.py collectstatic --noinput --clear

say "Products"
PRODUCT_COUNT="$(run_py -c 'import django; django.setup(); from supermarket.models import Product; print(Product.objects.count())')"
if [ "$PRODUCT_COUNT" = "0" ]; then
    echo "Empty catalogue — loading it from supermarket/fixtures/catalogue.json."
    run_py manage.py populate_data
else
    echo "$PRODUCT_COUNT products already in the shop — leaving them alone."
fi
# Only fills products that have no picture, so real photos are never replaced.
run_py manage.py add_product_images

say "Web app"
if [ -f "$WSGI_FILE" ]; then
    cp "$PROJECT_DIR/deploy/pythonanywhere_wsgi.py" "$WSGI_FILE"
    echo "Installed the WSGI file at $WSGI_FILE"
else
    cat <<INSTRUCTIONS
There's no web app yet. On the PythonAnywhere **Web** tab:

  1. "Add a new web app" -> Manual configuration -> $PYTHON
  2. Fill in:
       Source code:       $PROJECT_DIR
       Working directory: $PROJECT_DIR
       Virtualenv:        $VENV_DIR
  3. Under "Static files" add:
       URL: /static/   Directory: $PROJECT_DIR/staticfiles/
  4. Tick "Force HTTPS".
  5. Run this script again — it will then install the WSGI file itself.
INSTRUCTIONS
fi

if ! run_py -c 'import django; django.setup(); from django.contrib.auth.models import User; raise SystemExit(0 if User.objects.filter(is_superuser=True).exists() else 1)'; then
    say "Admin account"
    echo "No admin user yet. Create one now — this is the login for /admin/ and the dashboard at /founder/."
    run_py manage.py createsuperuser
fi

say "Finished"
echo "Press Reload on the Web tab, then open https://$DOMAIN"
