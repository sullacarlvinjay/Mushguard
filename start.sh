#!/bin/bash
echo "Running migrations..."
python manage.py migrate
echo "Making user admin..."
python make_admin.py
echo "Admin script completed"
echo "Starting server..."
gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT