#!/bin/bash

# Install Playwright browsers if not already installed
# if [ ! -d "/home/flaskuser/.cache/ms-playwright" ] || [ -z "$(ls -A /home/flaskuser/.cache/ms-playwright 2>/dev/null)" ]; then
#     echo "Installing Playwright browsers..."
#     python -m playwright install-deps || echo "Warning: Could not install system dependencies"
#     python -m playwright install chromium || echo "Warning: Could not install Chromium"
# fi

# Extract database host and port from DATABASE_URL or use defaults
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-5432}

# If using DATABASE_URL, extract host and port
if [ ! -z "$DATABASE_URL" ]; then
    # Extract host and port from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    # Fallback if extraction fails
    if [ -z "$DB_HOST" ]; then
        DB_HOST="localhost"
    fi
    if [ -z "$DB_PORT" ]; then
        DB_PORT="5432"
    fi
fi

echo "Waiting for database at $DB_HOST:$DB_PORT to be ready..."

# Wait for database to be ready using netcat
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; then
        echo "Database is ready!"
        break
    else
        echo "Database is unavailable - sleeping"
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -eq $max_attempts ]; then
    echo "Failed to connect to database after $max_attempts attempts"
    echo "Please check your database configuration"
    exit 1
fi

# Run database migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    python manage.py db upgrade || echo "Migration failed or not applicable"
fi

# Execute the main command
echo "Starting application with command: $@"
exec "$@"