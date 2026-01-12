# worker.py (in project root)
#!/usr/bin/env python
"""
This file creates the Flask app context for Celery workers.
It's the entry point for Celery worker processes.
"""
import os

# Set default environment
os.environ.setdefault('FLASK_ENV', 'development')

# Create Flask app
from app import create_app
flask_app = create_app()

# The celery instance is now available in app.celery or via import
# This file doesn't need to do anything else!

if __name__ == '__main__':
    # Optional: Allow running this file directly for debugging
    print("Celery worker entry point")
    print(f"Flask app created: {flask_app}")