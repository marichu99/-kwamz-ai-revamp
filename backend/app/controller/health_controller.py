"""
Health Check Controller
Provides endpoints for monitoring application health
"""

from flask import Blueprint, jsonify
from app import db
import redis
import os

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Basic health check endpoint
    Returns 200 if the application is running
    """
    return jsonify({
        'status': 'healthy',
        'service': 'kwamz-ai-backend'
    }), 200


@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check - verifies all dependencies are available
    Used by Kubernetes/Docker health checks
    """
    checks = {
        'database': False,
        'redis': False
    }

    # Check database connection
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = True
    except Exception as e:
        checks['database'] = str(e)

    # Check Redis connection
    try:
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        checks['redis'] = True
    except Exception as e:
        checks['redis'] = str(e)

    # Determine overall status
    all_healthy = all(v is True for v in checks.values())
    status_code = 200 if all_healthy else 503

    return jsonify({
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks
    }), status_code


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Liveness check - simple check that the process is running
    Used to detect if the application needs to be restarted
    """
    return jsonify({
        'status': 'alive'
    }), 200
