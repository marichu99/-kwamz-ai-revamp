# app/commands/fraud_detection.py
import subprocess
import sys
from flask import current_app
from app import create_app, db
from app.model.user import User
from app.service.transaction_service import TransactionService
import logging

logger = logging.getLogger(__name__)

def run_fraud_detection(user_id: int):
    """Run fraud detection for a specific user."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get user
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return False
            
            logger.info(f"Starting fraud detection for user: {user.email}")
            
            # Initialize transaction service
            transaction_service = TransactionService()
            
            # Run fraud detection
            result = transaction_service.run_fraud_detection_for_user(user)
            
            logger.info(f"Fraud detection completed for user: {user.email}")
            logger.info(f"Results: {result.get('historical_report', {}).get('summary', {})}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error running fraud detection: {str(e)}", exc_info=True)
            return False