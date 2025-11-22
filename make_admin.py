#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin():
    username = 'admin'
    email = 'admin@mushguard.com'
    password = 'admin123'
    
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"Admin user '{username}' created successfully!")
    else:
        print(f"Admin user '{username}' already exists.")

if __name__ == '__main__':
    create_admin()