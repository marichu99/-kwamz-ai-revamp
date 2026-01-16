# app/tasks/fraud_detection_tasks.py
import logging
import redis
import os
from datetime import datetime, timedelta
from app import create_app, db
from app.model.user import User
from app.model.company import Company
from app.model.transaction import Transaction
from app.service.transaction_service import TransactionService
from app.celery_config import celery

logger = logging.getLogger(__name__)

# Redis key for tracking last periodic check time
LAST_PERIODIC_CHECK_KEY = 'fraud_detection:last_periodic_check'
DEFAULT_CHECK_INTERVAL_MINUTES = 30


def get_redis_client():
    """Get Redis client for tracking task state."""
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url)


def get_active_config():
    """Get the active fraud detection configuration from database."""
    from app.model.config import Config
    config = Config.query.filter_by(is_active=True).first()
    if not config:
        # Return default values if no active config
        return {
            'periodic_check_interval_minutes': DEFAULT_CHECK_INTERVAL_MINUTES,
            'analysis_period_days': 30,
            'max_transactions_per_check': 100
        }
    return {
        'periodic_check_interval_minutes': config.periodic_check_interval_minutes or DEFAULT_CHECK_INTERVAL_MINUTES,
        'analysis_period_days': config.analysis_period_days or 30,
        'max_transactions_per_check': config.max_transactions_per_check or 100
    }


@celery.task(bind=True, name='fraud_detection.daily_report', queue='fraud_detection')
def send_daily_fraud_report(self):
    """
    Celery beat task to send daily fraud reports to admins.
    Scheduled to run daily at 9 AM (configured in celery_config.py).
    """
    app = create_app()

    with app.app_context():
        try:
            logger.info(f"[Task {self.request.id}] Starting daily fraud report generation")

            transaction_service = TransactionService()
            transaction_service.send_daily_fraud_report()

            logger.info(f"[Task {self.request.id}] Daily fraud report completed")

            return {
                'status': 'success',
                'task': 'daily_report',
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[Task {self.request.id}] Error in daily report: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}


@celery.task(bind=True, name='fraud_detection.periodic_check', queue='fraud_detection')
def run_periodic_fraud_check(self):
    """
    Celery beat task to run periodic fraud detection for users whose companies have transactions.

    This task is triggered every minute by Celery Beat, but it checks the database
    Config table for the actual configured interval (periodic_check_interval_minutes).
    It uses Redis to track the last run time and only executes if enough time has passed.
    """
    app = create_app()

    with app.app_context():
        try:
            # Get active configuration from database
            config = get_active_config()
            check_interval = config['periodic_check_interval_minutes']

            logger.info(f"[Task {self.request.id}] Checking if periodic fraud check should run (interval: {check_interval} minutes)")

            # Check last run time from Redis
            try:
                redis_client = get_redis_client()
                last_run_str = redis_client.get(LAST_PERIODIC_CHECK_KEY)

                if last_run_str:
                    last_run = datetime.fromisoformat(last_run_str.decode('utf-8'))
                    minutes_since_last_run = (datetime.now() - last_run).total_seconds() / 60

                    if minutes_since_last_run < check_interval:
                        logger.info(
                            f"[Task {self.request.id}] Skipping - only {minutes_since_last_run:.1f} minutes since last run "
                            f"(configured interval: {check_interval} minutes)"
                        )
                        return {
                            'status': 'skipped',
                            'reason': f'Last run was {minutes_since_last_run:.1f} minutes ago (interval: {check_interval} min)',
                            'next_run_in': f'{check_interval - minutes_since_last_run:.1f} minutes',
                            'timestamp': datetime.now().isoformat()
                        }
            except Exception as redis_error:
                logger.warning(f"[Task {self.request.id}] Could not check Redis: {str(redis_error)}, proceeding with check")

            # Update last run time in Redis
            try:
                redis_client = get_redis_client()
                redis_client.set(LAST_PERIODIC_CHECK_KEY, datetime.now().isoformat())
                # Set expiry to 2x the interval to clean up old keys
                redis_client.expire(LAST_PERIODIC_CHECK_KEY, check_interval * 60 * 2)
            except Exception as redis_error:
                logger.warning(f"[Task {self.request.id}] Could not update Redis: {str(redis_error)}")

            logger.info(f"[Task {self.request.id}] Starting periodic fraud check")

            # Get users whose companies have transactions
            users_with_transactions = db.session.query(User).join(
                Company, Company.user_id == User.id
            ).join(
                Transaction, Transaction.company_id == Company.id
            ).distinct().all()

            logger.info(f"[Task {self.request.id}] Found {len(users_with_transactions)} users with company transactions")

            results = []
            transaction_service = TransactionService()

            for user in users_with_transactions:
                try:
                    logger.info(f"[Task {self.request.id}] Running fraud check for user: {user.email}")

                    # Run fraud detection for this user
                    result = transaction_service.run_fraud_detection_for_user_sync(user.id)
                    results.append({
                        'user_id': user.id,
                        'email': user.email,
                        'status': result.get('status', 'unknown')
                    })

                except Exception as user_error:
                    logger.error(f"[Task {self.request.id}] Error for user {user.email}: {str(user_error)}")
                    results.append({
                        'user_id': user.id,
                        'email': user.email,
                        'status': 'error',
                        'error': str(user_error)
                    })

            logger.info(f"[Task {self.request.id}] Periodic fraud check completed for {len(results)} users")

            return {
                'status': 'success',
                'task': 'periodic_check',
                'configured_interval_minutes': check_interval,
                'users_processed': len(results),
                'results': results,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"[Task {self.request.id}] Error in periodic check: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

@celery.task(bind=True, name='fraud_detection.run_for_user', queue='fraud_detection', max_retries=3)
def run_fraud_detection_for_user(self, user_id: int):
    """
    Celery task to run fraud detection for a user.
    COMPLETELY SYNCHRONOUS VERSION
    """
    app = create_app()
    
    with app.app_context():
        try:
            logger.info(f"[Task {self.request.id}] Starting fraud detection for user_id: {user_id}")
            
            # Update task state
            self.update_state(
                state='PROGRESS',
                meta={'current': 10, 'total': 100, 'status': 'Starting...'}
            )
            
            # Get user
            user = User.query.get(user_id)
            if not user:
                logger.error(f"[Task {self.request.id}] User {user_id} not found")
                return {'status': 'error', 'message': 'User not found'}
            
            # Initialize transaction service
            transaction_service = TransactionService()
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': 30, 'total': 100, 'status': 'Running detection...'}
            )
            
            # Run detection - SYNC VERSION
            result = transaction_service.run_fraud_detection_for_user_sync(user_id)
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': 90, 'total': 100, 'status': 'Sending notifications...'}
            )
            
            logger.info(f"[Task {self.request.id}] Fraud detection completed for user: {user.email}")
            
            return result
                
        except Exception as e:
            logger.error(f"[Task {self.request.id}] Error running task: {str(e)}", exc_info=True)
            # Don't retry for now, just return error
            return {'status': 'error', 'message': str(e)}