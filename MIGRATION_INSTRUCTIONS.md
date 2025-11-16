# MIGRATION INSTRUCTIONS

## After implementing all code changes, run these commands:

### 1. Create migrations for auth_api
```bash
python manage.py makemigrations auth_api
```

### 2. Create migrations for core (user field added to ResearchSession)
```bash
python manage.py makemigrations core
```

### 3. Apply all migrations
```bash
python manage.py migrate
```

### 4. (Optional) Create a superuser for admin access
```bash
python manage.py createsuperuser
```

## Expected Migrations:

### auth_api migrations will create:
- UserProfile table
- UserSession table
- LoginAttempt table
- PasswordReset table

### core migrations will:
- Add 'user' field to ResearchSession table
- Add index on 'user' field for performance

## Note on existing data:
- Existing ResearchSessions will have `user=NULL` initially
- This is fine for development
- In production, you may want to assign orphaned sessions to a default user

## Verify migrations succeeded:
```bash
python manage.py showmigrations
```

All migrations should show [X] indicating they're applied.
