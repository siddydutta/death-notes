#!/bin/bash

set -e

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start server
python manage.py runserver 0.0.0.0:8000
