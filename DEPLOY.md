# Deployment

The app is deployed on **Railway** at
https://web-production-7cb68.up.railway.app

GitHub Pages cannot host this project. Pages serves static files only, and this
is a Django app with a database, authentication and a cart. The empty
`index.html` at the repository root is a leftover from an attempt at that and
has no effect.

## How the Railway project is put together

The project `shopping-app` contains two services:

| Service | What it is |
| --- | --- |
| `web` | This repository, built with Railpack and served by gunicorn |
| `Postgres` | The database, on a persistent volume |

Railway's application filesystem is wiped on every deploy, so SQLite is not
usable there — every order and account would vanish on redeploy. `settings.py`
therefore switches to Postgres whenever `DATABASE_URL` is present and keeps
SQLite for local development.

### Environment variables on the `web` service

| Variable | Value | Why |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | *(generated, secret)* | Signs sessions and CSRF tokens. The value committed in the repo's history is a public placeholder and must never be used. |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | A Railway reference, so it tracks the database service automatically. |
| `DJANGO_SECURE_SSL_REDIRECT` | `1` | Redirects HTTP to HTTPS. Set to `0` if you ever hit a redirect loop. |
| `PYTHON_VERSION` | `3.11` | Belt-and-braces alongside `.python-version`. |
| `RAILWAY_PUBLIC_DOMAIN` | *(injected by Railway)* | `settings.py` appends it to `ALLOWED_HOSTS`, so a new domain works without editing anything. |

`DJANGO_DEBUG` is deliberately unset: `settings.py` treats anything other than
`1` as debug-off, which is what production wants.

### Start command

From the [`Procfile`](Procfile):

```
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn zimbabwe_supermarket.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --log-file -
```

`collectstatic` runs on start rather than at build time because `staticfiles/`
is gitignored, so it does not exist in the container otherwise and WhiteNoise
would have nothing to serve — the site would load with no styling.

## Deploying a change

```bash
git push origin main
railway up --service web
```

`railway up` uploads the working directory. To have Railway build from GitHub
automatically on every push instead, connect the repository to the `web`
service in the Railway dashboard under **Settings → Source**.

## One-off commands against production

```bash
railway ssh --service web "python manage.py <command>"
```

Used for the initial setup:

```bash
railway ssh --service web "python manage.py populate_data"
railway ssh --service web "python manage.py createsuperuser --noinput --username admin --email you@example.com"
```

`populate_data` uses `get_or_create`, so re-running it will not duplicate
categories or products.

## Admin access

Django admin is at `/admin/`, and the founder dashboard at `/founder/`.

Access to `/founder/` requires **staff status**, which only a superuser can
grant. Grant it in Django admin under **Users → (pick user) → Staff status**.

> This previously worked by comparing the user's profile phone number against a
> hardcoded number. That number is printed publicly on the contact and delivery
> pages, and users can edit their own phone number, so anyone who registered
> could read every customer's messages, orders and home addresses. Do not
> reintroduce a check of that shape.

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

## Troubleshooting

Logs: `railway logs --service web`, build logs: `railway logs --build --service web`.

| Symptom | Cause |
| --- | --- |
| HTTP 400 on every page | The domain is not in `ALLOWED_HOSTS`. Redeploy so `RAILWAY_PUBLIC_DOMAIN` is present in the container, or set `DJANGO_ALLOWED_HOSTS` explicitly. |
| Site loads with no CSS | `collectstatic` did not run — check the start command and the build logs. |
| `No directory at: /app/staticfiles/` | Same cause as above. |
| Build fails compiling a dependency | The Python version drifted. Check `.python-version` is committed — it sits under a `# pyenv` rule in `.gitignore` that previously excluded it. |
| Data disappeared after a deploy | The app fell back to SQLite. Confirm `DATABASE_URL` is set on the `web` service. |
