web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn zimbabwe_supermarket.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --log-file -
