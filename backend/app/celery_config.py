# app/celery_config.py
import os
from celery import Celery
from celery.schedules import crontab

# Create Celery instance
celery = Celery(
    __name__,
    include=['app.tasks.fraud_detection_tasks']
)

def init_celery(app):
    """
    Initialize Celery with Flask app configuration.
    Call this from your create_app() function.
    """
    # Configure broker and backend
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Africa/Nairobi',
        enable_utc=True,
        broker_connection_retry_on_startup=True,
    )
    
    # Update with app config (for any CELERY_* prefixed settings)
    celery.conf.update(app.config)
    
    # Task routing configuration
    celery.conf.task_routes = {
        'fraud_detection.*': {'queue': 'fraud_detection'},
    }
    
    # Task annotations (rate limiting, etc.)
    celery.conf.task_annotations = {
        'fraud_detection.*': {'rate_limit': '10/m'},  # 10 tasks per minute
    }
    
    # Worker settings
    celery.conf.worker_max_tasks_per_child = 1000
    celery.conf.worker_prefetch_multiplier = 1
    
    # Beat schedule for periodic tasks
    # Note: periodic-fraud-check runs every minute but the task itself checks
    # the configurable interval from the database Config table
    celery.conf.beat_schedule = {
        'send-daily-fraud-report': {
            'task': 'fraud_detection.daily_report',
            'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
            'options': {'queue': 'fraud_detection'}
        },
        'periodic-fraud-check': {
            'task': 'fraud_detection.periodic_check',
            'schedule': crontab(minute='*/1'),  # Every minute - task checks DB config for actual interval
            'options': {'queue': 'fraud_detection'}
        },
    }
    
    # Set up Flask app context for tasks
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    
    return celery

# Optional: Make celery available for import
__all__ = ['celery', 'init_celery']