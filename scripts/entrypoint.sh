#!/bin/bash

set -e

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver 0.0.0.0:8000
