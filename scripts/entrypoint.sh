#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py shell -c "
from django.contrib.auth import get_user_model
from os import getenv
User = get_user_model()
username = getenv('DJANGO_SUPERUSER_USERNAME')
email = getenv('DJANGO_SUPERUSER_EMAIL')
password = getenv('DJANGO_SUPERUSER_PASSWORD')
if username and email and password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
"

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
