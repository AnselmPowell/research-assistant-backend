#!/usr/bin/env python
"""
Script to clear all data from Neon PostgreSQL database and reset migrations.
Run this to start fresh with your auth system.
"""

import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'research_assistant.settings')
django.setup()

from django.core.management import call_command
from django.db import connection
from django.contrib.auth.models import User


def clear_database():
    """Clear all tables and reset the database."""
    print("\n" + "="*60)
    print("🗑️  DATABASE RESET SCRIPT")
    print("="*60)
    
    # Confirm action
    print("\n⚠️  WARNING: This will DELETE ALL DATA from your database!")
    print("⚠️  This action CANNOT be undone!")
    confirmation = input("\nType 'YES' to proceed: ")
    
    if confirmation != 'YES':
        print("\n❌ Operation cancelled.")
        return
    
    print("\n" + "="*60)
    print("Starting database reset...")
    print("="*60)
    
    try:
        # Step 1: Get all table names
        print("\n[Step 1/5] Fetching all tables...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            print(f"✓ Found {len(tables)} tables")
        
        # Step 2: Drop all tables
        print("\n[Step 2/5] Dropping all tables...")
        with connection.cursor() as cursor:
            # For Neon, we use CASCADE to handle foreign keys
            for table in tables:
                try:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                    print(f"  ✓ Dropped table: {table}")
                except Exception as e:
                    print(f"  ⚠️  Could not drop {table}: {e}")
        
        print("✓ All tables dropped successfully")
        
        # Step 3: Delete migration files (except __init__.py)
        print("\n[Step 3/5] Cleaning migration files...")
        apps_to_clean = ['auth_api', 'core']
        
        for app in apps_to_clean:
            migrations_dir = f'{app}/migrations'
            if os.path.exists(migrations_dir):
                for file in os.listdir(migrations_dir):
                    if file.endswith('.py') and file != '__init__.py':
                        file_path = os.path.join(migrations_dir, file)
                        os.remove(file_path)
                        print(f"  ✓ Removed: {migrations_dir}/{file}")
        
        print("✓ Migration files cleaned")
        
        # Step 4: Create fresh migrations
        print("\n[Step 4/5] Creating fresh migrations...")
        call_command('makemigrations', 'auth_api', verbosity=1)
        call_command('makemigrations', 'core', verbosity=1)
        print("✓ Fresh migrations created")
        
        # Step 5: Apply migrations
        print("\n[Step 5/5] Applying migrations...")
        call_command('migrate', verbosity=1)
        print("✓ Migrations applied successfully")
        
        print("\n" + "="*60)
        print("✅ DATABASE RESET COMPLETE!")
        print("="*60)
        print("\n📋 Next steps:")
        print("  1. Create superuser: python manage.py createsuperuser")
        print("  2. Start backend: python manage.py runserver")
        print("  3. Test authentication from frontend")
        print("\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR: {str(e)}")
        print("="*60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    clear_database()
