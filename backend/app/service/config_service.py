from app.model.config import Config, DetectionLog, SuspiciousAccount
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename

from app import db

class ConfigService:
    """Service for managing fraud detection configurations"""
    
    @staticmethod
    def get_all_configs():
        """Get all configurations"""
        return Config.query.order_by(Config.updated_at.desc()).all()
    
    @staticmethod
    def get_config_by_id(config_id):
        """Get configuration by ID"""
        return Config.query.get(config_id)
    
    @staticmethod
    def get_active_config():
        """Get active configuration"""
        return Config.query.filter_by(is_active=True).first()
    
    @staticmethod
    def create_config(data, created_by=None):
        """Create new configuration"""
        # Ensure only one active config
        if data.get('is_active', False):
            ConfigService.deactivate_all_configs()
        
        config = Config(
            name=data.get('name', 'New Configuration'),
            description=data.get('description', ''),
            
            # SMTP Configuration
            smtp_server=data.get('smtp_server', 'smtp.gmail.com'),
            smtp_port=data.get('smtp_port', 587),
            sender_email=data.get('sender_email', ''),
            sender_password=data.get('sender_password', ''),
            recipient_emails=data.get('recipient_emails', 'fraud-team@company.com'),
            
            # Detection Parameters
            time_window_minutes=data.get('time_window_minutes', 5),
            amount_variance=data.get('amount_variance', 0.1),
            min_transactions_rollover=data.get('min_transactions_rollover', 3),
            split_threshold=data.get('split_threshold', 2),
            rapid_back_forth_threshold=data.get('rapid_back_forth_threshold', 2),
            
            # Risk Thresholds
            high_risk_score=data.get('high_risk_score', 50),
            medium_risk_score=data.get('medium_risk_score', 30),
            
            # Notification Settings
            email_enabled=data.get('email_enabled', False),
            notify_high_risk=data.get('notify_high_risk', True),
            notify_medium_risk=data.get('notify_medium_risk', False),
            notify_split_transactions=data.get('notify_split_transactions', True),
            notify_rollover_fraud=data.get('notify_rollover_fraud', True),
            notify_rapid_patterns=data.get('notify_rapid_patterns', True),
            
            # Email Settings
            email_subject_prefix=data.get('email_subject_prefix', '[Fraud Alert] '),
            
            # System Settings
            is_active=data.get('is_active', False),
            created_by=created_by
        )
        
        db.session.add(config)
        db.session.commit()
        return config
    
    @staticmethod
    def update_config(config_id, data):
        """Update existing configuration"""
        config = Config.query.get_or_404(config_id)
        
        # Ensure only one active config
        if data.get('is_active', False) and not config.is_active:
            ConfigService.deactivate_all_configs()
        
        # Update fields
        for key, value in data.items():
            if hasattr(config, key) and key not in ['id', 'created_at', 'created_by']:
                setattr(config, key, value)
        
        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config
    
    @staticmethod
    def delete_config(config_id):
        """Delete configuration"""
        config = Config.query.get_or_404(config_id)
        
        # Don't delete if it's active
        if config.is_active:
            raise ValueError("Cannot delete active configuration")
        
        db.session.delete(config)
        db.session.commit()
        return True
    
    @staticmethod
    def deactivate_all_configs():
        """Deactivate all configurations"""
        Config.query.update({'is_active': False})
        db.session.commit()
    
    @staticmethod
    def activate_config(config_id):
        """Activate a specific configuration"""
        ConfigService.deactivate_all_configs()
        
        config = Config.query.get_or_404(config_id)
        config.is_active = True
        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config
    
    @staticmethod
    def validate_config_data(data):
        """Validate configuration data"""
        errors = []
        
        # SMTP Validation
        if data.get('email_enabled', False):
            if not data.get('smtp_server'):
                errors.append('SMTP server is required when email is enabled')
            if not data.get('sender_email'):
                errors.append('Sender email is required when email is enabled')
            if not data.get('recipient_emails'):
                errors.append('At least one recipient email is required')
        
        # Detection Parameters Validation
        if data.get('time_window_minutes', 0) < 1 or data.get('time_window_minutes', 0) > 60:
            errors.append('Time window must be between 1 and 60 minutes')
        
        if data.get('amount_variance', 0) < 0.01 or data.get('amount_variance', 0) > 1.0:
            errors.append('Amount variance must be between 0.01 and 1.0')
        
        if data.get('min_transactions_rollover', 0) < 2:
            errors.append('Minimum transactions for roll-over must be at least 2')
        
        # Risk Thresholds Validation
        if data.get('high_risk_score', 0) < data.get('medium_risk_score', 0):
            errors.append('High risk score must be greater than medium risk score')
        
        return errors


class DetectionService:
    """Service for managing fraud detection runs"""
    
    @staticmethod
    def create_detection_log(config_id, initiated_by=None):
        """Create a new detection log"""
        log = DetectionLog(
            config_id=config_id,
            status='pending',
            initiated_by=initiated_by
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def update_detection_log(log_id, data):
        """Update detection log"""
        log = DetectionLog.query.get_or_404(log_id)
        
        for key, value in data.items():
            if hasattr(log, key):
                setattr(log, key, value)
        
        db.session.commit()
        return log
    
    @staticmethod
    def save_suspicious_accounts(detection_log_id, accounts_data):
        """Save suspicious accounts from detection run"""
        for account_data in accounts_data:
            account = SuspiciousAccount(
                detection_log_id=detection_log_id,
                phone_number=account_data['phone_number'],
                account_name=account_data.get('account_name', ''),
                fraud_score=account_data['fraud_score'],
                risk_level=account_data['risk_level'],
                suspicious_transactions=account_data['suspicious_transactions'],
                total_amount=account_data['total_amount'],
                split_detected=account_data.get('split_detected', False),
                rollover_detected=account_data.get('rollover_detected', False),
                rapid_detected=account_data.get('rapid_detected', False)
            )
            db.session.add(account)
        
        db.session.commit()
    
    @staticmethod
    def get_detection_logs(page=1, per_page=20):
        """Get paginated detection logs"""
        return DetectionLog.query.order_by(
            DetectionLog.started_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_detection_log_by_id(log_id):
        """Get detection log by ID"""
        return DetectionLog.query.get_or_404(log_id)