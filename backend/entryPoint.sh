#!/bin/bash

# Set default display
export DISPLAY=:99

# Start Xvfb for headless=False support if not using host display
if [ "$USE_HOST_DISPLAY" != "true" ]; then
    echo "Starting virtual display on $DISPLAY..."
    # Clean up any stale lock/socket files from a previous container run
    rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true

    Xvfb $DISPLAY -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!

    sleep 2

    # Use kill -0 instead of ps (ps not available in slim image)
    if kill -0 $XVFB_PID 2>/dev/null; then
        echo "Xvfb started successfully (PID: $XVFB_PID)"
    else
        echo "Warning: Xvfb failed to start. Headless mode may not work properly."
    fi
else
    echo "Using host display: $DISPLAY"
fi

# Optional: Start VNC server for remote debugging
if [ "$ENABLE_VNC" = "true" ]; then
    echo "Starting VNC server on port 5900..."
    x11vnc -display $DISPLAY -forever -shared -rfbport 5900 -passwd "${VNC_PASSWORD:-vncpassword}" &
    VNC_PID=$!
    echo "VNC server started (PID: $VNC_PID)"
fi

# Install Playwright browsers if not already installed
if [ ! -d "/home/flaskuser/.cache/ms-playwright" ] || [ -z "$(ls -A /home/flaskuser/.cache/ms-playwright 2>/dev/null)" ]; then
    echo "Installing Playwright browsers..."
    playwright install-deps || echo "Warning: Could not install system dependencies"
    playwright install chromium || echo "Warning: Could not install Chromium"
    
    # Install additional browsers if needed
    if [ "$INSTALL_FIREFOX" = "true" ]; then
        playwright install firefox
    fi
    if [ "$INSTALL_WEBKIT" = "true" ]; then
        playwright install webkit
    fi
fi

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

# Health check for Xvfb if running in headful mode
if [ "$USE_HOST_DISPLAY" != "true" ] && [ "$CHECK_XVFB" = "true" ]; then
    echo "Checking if Xvfb is ready..."
    if xdpyinfo -display $DISPLAY >/dev/null 2>&1; then
        echo "Xvfb is ready on display $DISPLAY"
    else
        echo "Warning: Xvfb is not responding on display $DISPLAY"
    fi
fi

# Execute the main command
echo "Starting application with command: $@"
exec "$@"