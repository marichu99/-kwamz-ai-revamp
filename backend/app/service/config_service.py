from app.model.config import Config, DetectionLog, SuspiciousAccount
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename

from app import db

class ConfigService:
    """Service for managing fraud detection configurations"""

    @staticmethod
    def get_all_configs(user_id):
        """Get all configurations for a specific user"""
        return Config.query.filter_by(user_id=user_id).order_by(Config.updated_at.desc()).all()

    @staticmethod
    def get_config_by_id(config_id, user_id):
        """Get configuration by ID, scoped to user"""
        return Config.query.filter_by(id=config_id, user_id=user_id).first()

    @staticmethod
    def get_active_config(user_id):
        """Get active configuration for a specific user"""
        return Config.query.filter_by(user_id=user_id, is_active=True).first()

    @staticmethod
    def create_config(data, user_id, created_by=None):
        """Create new configuration for a user"""
        # Ensure only one active config per user
        if data.get('is_active', False):
            ConfigService.deactivate_all_configs(user_id)

        config = Config(
            user_id=user_id,
            name=data.get('name', 'New Configuration'),
            description=data.get('description', ''),

            # Detection Parameters
            time_window_minutes=data.get('time_window_minutes', 5),
            amount_variance=data.get('amount_variance', 0.1),
            min_transactions_rollover=data.get('min_transactions_rollover', 3),
            split_threshold=data.get('split_threshold', 5),
            rapid_back_forth_threshold=data.get('rapid_back_forth_threshold', 2),

            # Split Transaction Thresholds
            split_min_amount=data.get('split_min_amount', 100.0),
            split_max_amount=data.get('split_max_amount', 50000.0),
            split_total_amount_threshold=data.get('split_total_amount_threshold', 10000.0),

            # Periodic Check Settings
            periodic_check_interval_minutes=data.get('periodic_check_interval_minutes', 30),
            analysis_period_days=data.get('analysis_period_days', 30),
            max_transactions_per_check=data.get('max_transactions_per_check', 100),

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
            created_by=created_by,

            # Per-fraud-type configuration
            fraud_type_configs=data.get('fraud_type_configs'),
        )

        db.session.add(config)
        db.session.commit()
        return config

    @staticmethod
    def update_config(config_id, user_id, data):
        """Update existing configuration, verifying ownership"""
        config = Config.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError("Configuration not found")

        # Ensure only one active config per user
        if data.get('is_active', False) and not config.is_active:
            ConfigService.deactivate_all_configs(user_id)

        # Update fields (SMTP fields are managed globally via SmtpConfig)
        smtp_keys = {'smtp_server', 'smtp_port', 'sender_email', 'sender_password', 'recipient_emails'}
        for key, value in data.items():
            if hasattr(config, key) and key not in ['id', 'created_at', 'created_by', 'user_id'] and key not in smtp_keys:
                setattr(config, key, value)

        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config

    @staticmethod
    def delete_config(config_id, user_id):
        """Delete configuration, verifying ownership"""
        config = Config.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError("Configuration not found")

        # Don't delete if it's active
        if config.is_active:
            raise ValueError("Cannot delete active configuration")

        db.session.delete(config)
        db.session.commit()
        return True

    @staticmethod
    def deactivate_all_configs(user_id):
        """Deactivate all configurations for a specific user"""
        Config.query.filter_by(user_id=user_id).update({'is_active': False})
        db.session.commit()

    @staticmethod
    def activate_config(config_id, user_id):
        """Activate a specific configuration, scoped to user"""
        ConfigService.deactivate_all_configs(user_id)

        config = Config.query.filter_by(id=config_id, user_id=user_id).first()
        if not config:
            raise ValueError("Configuration not found")
        config.is_active = True
        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config

    @staticmethod
    def validate_config_data(data):
        """Validate configuration data"""
        errors = []

        # Detection Parameters Validation
        time_window = data.get('time_window_minutes', 5)
        if time_window < 1 or time_window > 60:
            errors.append('Time window must be between 1 and 60 minutes')

        amount_variance = data.get('amount_variance', 0.1)
        if amount_variance < 0.01 or amount_variance > 1.0:
            errors.append('Amount variance must be between 0.01 and 1.0')

        if data.get('min_transactions_rollover', 3) < 2:
            errors.append('Minimum transactions for roll-over must be at least 2')

        # Split Transaction Threshold Validation
        split_threshold = data.get('split_threshold', 5)
        if split_threshold < 2 or split_threshold > 50:
            errors.append('Split threshold must be between 2 and 50 transactions')

        split_min = data.get('split_min_amount', 100.0)
        split_max = data.get('split_max_amount', 50000.0)
        if split_min < 0:
            errors.append('Split minimum amount cannot be negative')
        if split_max < split_min:
            errors.append('Split maximum amount must be greater than minimum amount')

        split_total = data.get('split_total_amount_threshold', 10000.0)
        if split_total < 0:
            errors.append('Split total amount threshold cannot be negative')

        # Periodic Check Validation
        periodic_interval = data.get('periodic_check_interval_minutes', 30)
        if periodic_interval < 1 or periodic_interval > 1440:
            errors.append('Periodic check interval must be between 1 and 1440 minutes (24 hours)')

        # Risk Thresholds Validation
        if data.get('high_risk_score', 0) < data.get('medium_risk_score', 0):
            errors.append('High risk score must be greater than medium risk score')

        # Fraud Type Configs Validation
        fraud_type_configs = data.get('fraud_type_configs')
        if fraud_type_configs and isinstance(fraud_type_configs, dict):
            valid_types = set(Config.FRAUD_TYPE_DEFAULTS.keys())
            for fraud_type, type_config in fraud_type_configs.items():
                if fraud_type not in valid_types:
                    errors.append(f'Unknown fraud type: {fraud_type}')
                    continue
                if not isinstance(type_config, dict):
                    errors.append(f'Config for {fraud_type} must be an object')
                    continue
                # Validate time_window_minutes if present
                tw = type_config.get('time_window_minutes')
                if tw is not None and (tw < 1 or tw > 60):
                    errors.append(f'{fraud_type}: Time window must be between 1 and 60 minutes')
                # Validate amount_variance if present
                av = type_config.get('amount_variance')
                if av is not None and (av < 0.01 or av > 1.0):
                    errors.append(f'{fraud_type}: Amount variance must be between 0.01 and 1.0')

        return errors

    @staticmethod
    def get_fraud_type_info():
        """Return fraud type metadata for the frontend."""
        result = {}
        for fraud_type, info in Config.FRAUD_TYPE_INFO.items():
            defaults = Config.FRAUD_TYPE_DEFAULTS.get(fraud_type, {})
            result[fraud_type] = {
                **info,
                'defaults': defaults,
            }
        return result


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
