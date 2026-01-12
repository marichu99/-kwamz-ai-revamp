# app/tasks/fraud_detection_tasks.py
import asyncio
import logging
from celery import current_task
from app import create_app, db
from app.model.user import User
from app.service.transaction_service import TransactionService

logger = logging.getLogger(__name__)

# Import celery from your config
from app.config.celery_config import celery

@celery.task(bind=True, name='fraud_detection.run_for_user', max_retries=3)
def run_fraud_detection_for_user(self, user_id: int):
    """
    Celery task to run fraud detection for a user.
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize transaction service
            transaction_service = TransactionService()
            
            # Update task state
            self.update_state(
                state='PROGRESS',
                meta={'current': 0, 'total': 100, 'status': 'Starting...'}
            )
            
            # Run async detection
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    transaction_service.run_fraud_detection_for_user_async(user_id)
                )
                
                logger.info(f"Task {self.request.id}: Fraud detection completed for user {user_id}")
                return result
                
            except Exception as e:
                logger.error(f"Task {self.request.id}: Error in fraud detection: {str(e)}", exc_info=True)
                raise self.retry(exc=e, countdown=60)
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Task {self.request.id}: Error running task: {str(e)}", exc_info=True)
            return {'status': 'error', 'message': str(e)}

@celery.task(name='fraud_detection.daily_report', ignore_result=True)
def send_daily_fraud_report():
    """Send daily fraud report to all admins."""
    app = create_app()
    
    with app.app_context():
        try:
            transaction_service = TransactionService()
            transaction_service.send_daily_fraud_report()
            logger.info("Daily fraud report task completed")
        except Exception as e:
            logger.error(f"Error in daily report task: {str(e)}", exc_info=True)

@celery.task(name='fraud_detection.periodic_check', ignore_result=True)
def run_periodic_fraud_check():
    """Run periodic fraud check."""
    app = create_app()
    
    with app.app_context():
        try:
            transaction_service = TransactionService()
            transaction_service.run_periodic_fraud_check()
            logger.info("Periodic fraud check task completed")
        except Exception as e:
            logger.error(f"Error in periodic check task: {str(e)}", exc_info=True)