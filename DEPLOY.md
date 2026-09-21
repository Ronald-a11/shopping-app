# Deployment

The shop is hosted on **PythonAnywhere** (free tier), at
`https://<your-pythonanywhere-username>.pythonanywhere.com`.

> Railway hosted it until 21 September 2026, when the free trial expired and
> the site stopped serving. That project still exists but is dormant; its
> settings are kept at the end of this file in case you go back to it.

GitHub Pages cannot host this project. Pages serves static files only, and this
is a Django app with a database, authentication and a cart. The empty
`index.html` at the repository root is a leftover from an attempt at that and
has no effect.

## First deploy

You need a free PythonAnywhere account. The username becomes the web address,
so pick it with that in mind.

**1. In a Bash console** (Consoles → Bash):

```bash
git clone https://github.com/Ronald-a11/shopping-app.git ~/shopping-app
bash ~/shopping-app/deploy/pythonanywhere_setup.sh
```

It creates the virtualenv, installs the packages, writes `~/.jkc_env` with a
freshly generated secret key, migrates the database, collects the static files
and adds the sample products. It ends by printing what to do next.

**2. On the Web tab**: *Add a new web app* → **Manual configuration** → the
Python version the script printed, then set:

| Field | Value |
| --- | --- |
| Source code | `/home/<username>/shopping-app` |
| Working directory | `/home/<username>/shopping-app` |
| Virtualenv | `/home/<username>/.virtualenvs/jkc` |
| Static files: URL `/static/` | Directory `/home/<username>/shopping-app/staticfiles/` |

Tick **Force HTTPS**.

**3. Back in the console**, run the script again. Now that the web app exists,
it installs [`deploy/pythonanywhere_wsgi.py`](deploy/pythonanywhere_wsgi.py)
over the Web tab's WSGI file and offers to create your admin login.

**4. Press Reload** on the Web tab and open the site.

## Deploying a change

```bash
git push origin main          # from your computer
```

then, in a PythonAnywhere Bash console:

```bash
bash ~/shopping-app/deploy/pythonanywhere_setup.sh
```

and press **Reload** on the Web tab. The script is safe to re-run: it pulls,
installs anything new, migrates, refreshes the static files, leaves your
secret key and your products alone, and updates the WSGI file.

## How it is put together

| Piece | Where |
| --- | --- |
| Code | `~/shopping-app` (a clone of this repository) |
| Virtualenv | `~/.virtualenvs/jkc` |
| Database | SQLite at `~/shopping-app/db.sqlite3` — PythonAnywhere's disk is permanent, unlike Railway's |
| Secret key and hostname | `~/.jkc_env`, never committed; read by the WSGI file |
| Static files | `~/shopping-app/staticfiles`, served by PythonAnywhere, not Django |

`settings.py` reads `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and
`DJANGO_SECURE_SSL_REDIRECT` from the environment; on PythonAnywhere the WSGI
file loads them from `~/.jkc_env` before Django starts. HTTPS redirection is
left to the Web tab's **Force HTTPS** switch, because doing it in both places
can loop.

**Back up the database** by copying `db.sqlite3` (Files tab → Download, or
`cp ~/shopping-app/db.sqlite3 ~/backup-$(date +%F).sqlite3`). It holds every
order, account and message.

To move to MySQL later (included on the free plan), add `mysqlclient` to
`requirements.txt` and put the connection string in `~/.jkc_env` as
`DATABASE_URL=mysql://user:password@host/dbname`; `settings.py` already prefers
`DATABASE_URL` whenever it is set.

### Free-plan limits worth knowing

- The web app must be renewed every three months with a button on the Web tab.
  PythonAnywhere emails a reminder; miss it and the site stops until you click.
- One web app, on the `pythonanywhere.com` subdomain. A custom domain such as
  `jkcsupermarket.co.zw` needs their paid plan (about $5/month).
- There is a daily CPU allowance. Going over it makes things run slower rather
  than taking the site down.
- Free accounts can only reach allow-listed sites *from the server*. This app
  never makes outgoing requests — fonts, icons and product photos load in the
  visitor's browser — so it is not affected.

## One-off commands

In a Bash console:

```bash
cd ~/shopping-app && source ~/.virtualenvs/jkc/bin/activate
set -a; source ~/.jkc_env; set +a
python manage.py <command>
```

Useful ones:

```bash
python manage.py createsuperuser      # another admin login
python manage.py changepassword <username>
python manage.py populate_data        # the catalogue, into an empty shop
python manage.py add_product_images   # pictures for products that have none
python manage.py dump_catalogue       # save catalogue changes back to the repository
```

`populate_data` loads `supermarket/fixtures/catalogue.json` — the nine
categories and the products on sale, with prices, stock and pictures — and
refuses to run if the shop already has products, so it can never duplicate
them. After changing the catalogue on your own computer, run `dump_catalogue`
and commit the fixture; the next deploy then starts from the same shop.

`add_product_images` matches a product to
`static/images/products/<slugified name>.webp` and only fills in a blank
picture, so a photo set in Django admin is never overwritten. `--force`
replaces every picture; `--dry-run` shows what would change.

`tidy_catalogue` is a one-off that merged the duplicate categories and products
left by the old seed scripts. It has already been run; it is kept because it
documents which entries were merged and why.

## Admin access

Django admin is at `/admin/`, and the staff admin dashboard at `/founder/`
(overview, inventory, orders, deliveries, messages).

Change stock on the dashboard (`/founder/inventory/`), not in Django admin:
**Stock received** (or the quick Restock box in the list) for a delivery from a
supplier, **Correct the stock** for breakage, theft or a miscount. Both are
written to the stock log that "Stock bought" and the stock history are built
from, which is why stock is read-only in Django admin.

Access to `/founder/` requires **staff status**, which only a superuser can
grant. Grant it in Django admin under **Users → (pick user) → Staff status**.

> This previously worked by comparing the user's profile phone number against a
> hardcoded number. That number is printed publicly on the contact and delivery
> pages, and users can edit their own phone number, so anyone who registered
> could read every customer's messages, orders and home addresses. Do not
> reintroduce a check of that shape.

## Styling (Tailwind CSS)

Pages are styled with Tailwind CSS v4. The source is
[`frontend/src/app.css`](frontend/src/app.css) (the dark-blue `brand` and
`cream` palettes, plus shared component classes such as `btn`, `card`, `tabs`,
`toast`); the compiled, minified stylesheet is `static/css/app.css` and **is
committed**, so no server ever needs Node.js.

Tailwind only emits the utility classes it finds in `templates/`,
`supermarket/`, `static/js/main.js` and `static/js/dashboard.js` (the revenue
chart). After changing any of those, rebuild — otherwise newly used classes are
simply missing on the live site:

```bash
cd frontend
npm install      # first time only
npm run build    # or `npm run watch` while developing
```

Interactive behaviour (tabs, toasts, add-to-cart without a reload, confirm
dialogs, loaders, scroll animations) lives in `static/js/main.js` and is wired
up with `data-` attributes; the comment at the top of that file lists them.

## Local development

```bash
start.bat
```

Or manually — `DJANGO_DEBUG=1` matters, because with debug off Django enables
the HTTPS redirect and stops serving static files itself:

```bash
set DJANGO_DEBUG=1
python manage.py migrate
python manage.py runserver
```

Local runs use SQLite (`db.sqlite3`) because `DATABASE_URL` is not set.

Tests: `python manage.py test supermarket` (280 of them; set `DJANGO_DEBUG=1`
so the debug-only settings apply).

## Troubleshooting

Errors appear in the **error log** on the Web tab (`<username>.pythonanywhere.com.error.log`).

| Symptom | Cause |
| --- | --- |
| HTTP 400 on every page | The hostname is missing from `ALLOWED_HOSTS`. Check `DJANGO_ALLOWED_HOSTS` in `~/.jkc_env` matches the site's address, then Reload. |
| "Something went wrong :-(" on every page | An exception at startup — read the error log. Usually the virtualenv path on the Web tab, or the WSGI file not yet installed. |
| Site loads with no styling | `collectstatic` has not run, or the Web tab's static files mapping is missing or misspelt. Re-run the setup script, check the mapping, Reload. |
| A new Tailwind class has no effect | `static/css/app.css` was not rebuilt and committed. Run `npm run build` in `frontend/`. |
| Right colours and buttons, but no layout — menus and panels stacked, icons above their boxes | The browser has a half-downloaded stylesheet. Everything that positions things (`hidden`, `flex`, `absolute`, the breakpoints) sits in the second half of the file, so a partial copy styles the page without laying it out. Press Ctrl+Shift+R. It should not happen again: `npm run build` now writes to `frontend/.build/` and moves the finished file into place, and in development the stylesheet URL carries a stamp that changes with the file. |
| Changes don't show up | The Reload button was not pressed. Code changes need it every time. |
| Redirect loop | Django and PythonAnywhere both redirecting to HTTPS. Keep `DJANGO_SECURE_SSL_REDIRECT=0` in `~/.jkc_env` and leave it to Force HTTPS. |
| Site stopped after months of working | The three-month free-plan renewal. Press the button on the Web tab. |

## Railway (the previous host, dormant)

The project `shopping-app` on Railway had a `web` service (this repository,
built with Railpack and served by gunicorn from the [`Procfile`](Procfile)) and
a `Postgres` service. Railway wipes the application filesystem on every deploy,
which is why `settings.py` switches to Postgres whenever `DATABASE_URL` is
present and keeps SQLite for everywhere else.

Environment variables it used: `DJANGO_SECRET_KEY`,
`DATABASE_URL=${{Postgres.DATABASE_URL}}`, `DJANGO_SECURE_SSL_REDIRECT=1`,
`PYTHON_VERSION=3.11`, plus `RAILWAY_PUBLIC_DOMAIN`, which Railway injects and
`settings.py` appends to `ALLOWED_HOSTS`. Attach the domain *before* the first
deploy, or every request answers HTTP 400. Deploy with `railway up --service
web`; run one-off commands with `railway ssh --service web "python manage.py
<command>"`.

Reviving it needs a paid plan (about $5/month for Hobby).
