#!/bin/bash

# Wait for the database to be ready
if [ -n "$DATABASE_URL" ]; then
    echo "Waiting for database to be ready..."
    
    # Extract host and port from DATABASE_URL
    POSTGRES_HOST=$(echo $DATABASE_URL | sed -e 's/^.*@//' -e 's/\/.*$//' -e 's/:.*$//')
    POSTGRES_PORT=$(echo $DATABASE_URL | sed -e 's/^.*://' -e 's/\/.*$//')
    
    # If port is not specified, use default PostgreSQL port
    if [ "$POSTGRES_HOST" = "$POSTGRES_PORT" ]; then
        POSTGRES_PORT=5432
    fi
    
    # Wait for the database to be available
    until nc -z -v -w30 $POSTGRES_HOST $POSTGRES_PORT; do
      echo "Waiting for database connection..."
      sleep 2
    done
    
    echo "Database is ready!"
fi

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start server
echo "Starting server..."
exec "$@"
