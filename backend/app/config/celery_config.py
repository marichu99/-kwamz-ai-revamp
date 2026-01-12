# app/celery_config.py
import os
from celery import Celery
from celery.schedules import crontab

# Create Celery instance
def make_celery(app_name=__name__):
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    celery = Celery(
        app_name,
        broker=redis_url,
        backend=redis_url,
        include=['app.tasks.fraud_detection_tasks']
    )
    
    # Optional configuration
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Africa/Nairobi',
        enable_utc=True,
        task_routes={
            'fraud_detection.*': {'queue': 'fraud_detection'},
        },
        task_annotations={
            'fraud_detection.*': {'rate_limit': '10/m'}  # 10 tasks per minute
        },
        worker_max_tasks_per_child=1000,
        worker_prefetch_multiplier=1,
    )
    
    return celery

# Create celery instance
celery = make_celery()