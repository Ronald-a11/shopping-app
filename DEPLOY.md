# Deploying to PythonAnywhere

This project is a Django application, so it needs a Python host. GitHub Pages
cannot run it — Pages serves static files only, and this app has a database,
authentication, and a shopping cart.

PythonAnywhere's free tier is a good fit: it gives you one web app at
`<username>.pythonanywhere.com`, a real persistent filesystem (so the SQLite
database survives restarts and redeploys), and it needs no credit card.

Replace `YOURUSERNAME` throughout with your PythonAnywhere username.

---

## 1. Create the account

Sign up for a free "Beginner" account at https://www.pythonanywhere.com/registration/register/beginner/

Your site will be served at `YOURUSERNAME.pythonanywhere.com`.

## 2. Clone the repository

On the **Consoles** tab, start a **Bash** console and run:

```bash
git clone https://github.com/Ronald-a11/shopping-app.git
cd shopping-app
```

## 3. Create the virtualenv and install dependencies

```bash
mkvirtualenv --python=/usr/bin/python3.10 shopping-app
pip install -r requirements.txt
```

`mkvirtualenv` leaves the new environment active, and it will be created at
`/home/YOURUSERNAME/.virtualenvs/shopping-app`. You need that path in step 5.

## 4. Set up the database and static files

Still in the Bash console, from inside `~/shopping-app`:

```bash
export DJANGO_SECRET_KEY='the-key-you-generated'
export DJANGO_ALLOWED_HOSTS='YOURUSERNAME.pythonanywhere.com'
export DJANGO_STATIC_ROOT="$HOME/shopping-app/staticfiles"

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py populate_data
python manage.py createsuperuser
```

Notes:

- These `export`s apply only to this console session. The web app reads its
  configuration from the WSGI file in step 6 instead.
- `populate_data` uses `get_or_create`, so it is safe to re-run after future
  deployments — it will not duplicate categories or products.
- `createsuperuser` is interactive and creates your admin login for `/admin`.

## 5. Create the web app

On the **Web** tab:

1. **Add a new web app** → **Manual configuration** (*not* the "Django" option,
   which would scaffold a brand-new project over yours) → **Python 3.10**.
2. Under **Code**, set **Source code** to `/home/YOURUSERNAME/shopping-app`.
3. Under **Virtualenv**, enter
   `/home/YOURUSERNAME/.virtualenvs/shopping-app`.

## 6. Configure the WSGI file

Under **Code**, click the **WSGI configuration file** link
(`/var/www/YOURUSERNAME_pythonanywhere_com_wsgi.py`). Delete everything in it
and paste the contents of [`deploy/pythonanywhere_wsgi.py`](deploy/pythonanywhere_wsgi.py)
from this repository, filling in your username and secret key.

The secret key lives here rather than in the repository because `/var/www/` is
private to your account, while this repository is public.

## 7. Map the static and media files

Django does not serve static files when `DEBUG` is off — the web server must.
On the **Web** tab, under **Static files**, add two mappings:

| URL | Directory |
| --- | --- |
| `/static/` | `/home/YOURUSERNAME/shopping-app/staticfiles` |
| `/media/` | `/home/YOURUSERNAME/shopping-app/media` |

Skipping this is the usual cause of a site that loads but has no styling.

## 8. Reload

Press the green **Reload** button at the top of the Web tab, then visit
`https://YOURUSERNAME.pythonanywhere.com`.

---

## Deploying later changes

```bash
cd ~/shopping-app
git pull
workon shopping-app
python manage.py migrate
python manage.py collectstatic --noinput
```

Then press **Reload** on the Web tab. Code changes do not take effect until you
reload.

## Troubleshooting

Check the **Error log** link on the Web tab first — it has the traceback.

| Symptom | Cause |
| --- | --- |
| `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` in the WSGI file does not match your real domain. |
| Site loads, no CSS or images | The `/static/` mapping in step 7 is missing or points at the wrong directory, or `collectstatic` was never run. |
| `ImproperlyConfigured: SECRET_KEY` | `DJANGO_SECRET_KEY` is missing from the WSGI file. |
| Too many redirects | Set `DJANGO_SECURE_SSL_REDIRECT` to `'0'` in the WSGI file. |
| `OperationalError: no such table` | `migrate` was not run, or was run against a different directory. |
| Changes not showing | You did not press **Reload** after `git pull`. |

## Things to know about the free tier

- **Uploaded images** are written to `media/` on PythonAnywhere's disk. They
  persist, but they are not in git, so they are not backed up. Download them if
  they matter.
- **The database is SQLite** on a real disk, so data persists across reloads.
  Back it up by downloading `db.sqlite3` from the **Files** tab.
- **Free web apps expire every three months.** PythonAnywhere emails you a link
  to click to keep the site running; if you ignore it the site goes offline
  until you log in and renew.
- Free accounts can only make outbound network requests to allowlisted sites.
  This app does not make any, so it is not a problem today.
