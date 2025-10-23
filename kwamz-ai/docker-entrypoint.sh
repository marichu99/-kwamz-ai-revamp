#!/bin/bash

# Function to replace environment variables in JavaScript files
replace_env_vars() {
    echo "Replacing environment variables in built files..."
    
    # Find all JavaScript and HTML files
    find /usr/share/nginx/html -type f \( -name '*.js' -o -name '*.html' \) -exec sed -i \
        -e "s|VITE_API_URL_PLACEHOLDER|${VITE_API_URL:-http://localhost:5000/api}|g" \
        -e "s|VITE_APP_TITLE_PLACEHOLDER|${VITE_APP_TITLE:-My Vite App}|g" \
        {} \;
}

# Replace environment variables
replace_env_vars

# Start nginx
exec "$@"