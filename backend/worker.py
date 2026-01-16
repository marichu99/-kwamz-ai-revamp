# worker.py (in project root)
#!/usr/bin/env python
"""
Celery worker entry point.
"""
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set default environment
os.environ.setdefault('FLASK_ENV', 'development')

# Create Flask app - this initializes celery via init_celery()
from app import create_app
app = create_app()

# Import the celery instance (it's now properly configured)
from app.celery_config import celery

# Optional: Print configuration for debugging
if __name__ == '__main__':
    print("=" * 60)
    print("CELERY WORKER CONFIGURATION")
    print("=" * 60)
    print(f"App: {app}")
    print(f"Celery: {celery}")
    print(f"Broker URL: {celery.conf.broker_url}")
    print(f"Registered tasks: {list(celery.tasks.keys())}")
    print(f"Beat schedule: {celery.conf.beat_schedule}")
    print("=" * 60)