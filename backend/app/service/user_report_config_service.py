from app import db
from app.model.user_report_config import UserReportConfig
from datetime import datetime, timedelta


class UserReportConfigService:
    """Service for managing user report configurations"""

    @staticmethod
    def get_all_configs_for_user(user_id):
        """Get all report configurations for a user"""
        return UserReportConfig.query.filter_by(user_id=user_id).order_by(
            UserReportConfig.created_at.desc()
        ).all()

    @staticmethod
    def get_config_by_id(config_id):
        """Get a specific configuration by ID"""
        return UserReportConfig.query.get(config_id)

    @staticmethod
    def get_active_configs():
        """Get all active configurations (for scheduler)"""
        return UserReportConfig.query.filter_by(is_active=True).all()

    @staticmethod
    def get_due_configs():
        """Get configurations that are due to run"""
        now = datetime.utcnow()
        return UserReportConfig.query.filter(
            UserReportConfig.is_active == True,
            (UserReportConfig.next_run_at == None) | (UserReportConfig.next_run_at <= now)
        ).all()

    @staticmethod
    def create_config(data, user_id):
        """Create a new report configuration"""
        config = UserReportConfig(
            user_id=user_id,
            name=data.get('name'),
            description=data.get('description', ''),
            report_type=data.get('report_type'),
            frequency_value=data.get('frequency_value', 1),
            frequency_unit=data.get('frequency_unit', 'days'),
            recipient_emails=data.get('recipient_emails'),
            is_active=data.get('is_active', True),

            # Fraud Detection Parameters
            time_window_minutes=data.get('time_window_minutes', 5),
            amount_variance=data.get('amount_variance', 0.1),
            min_transactions_rollover=data.get('min_transactions_rollover', 3),
            split_threshold=data.get('split_threshold', 5),
            split_min_amount=data.get('split_min_amount', 100.0),
            split_max_amount=data.get('split_max_amount', 50000.0),
            split_total_amount_threshold=data.get('split_total_amount_threshold', 10000.0),
            rapid_back_forth_threshold=data.get('rapid_back_forth_threshold', 2),
            high_risk_score=data.get('high_risk_score', 50),
            medium_risk_score=data.get('medium_risk_score', 30),
            analysis_period_days=data.get('analysis_period_days', 30),
            max_transactions_per_check=data.get('max_transactions_per_check', 100),

            # Notification Settings
            notify_high_risk=data.get('notify_high_risk', True),
            notify_medium_risk=data.get('notify_medium_risk', False),
            notify_split_transactions=data.get('notify_split_transactions', True),
            notify_rollover_fraud=data.get('notify_rollover_fraud', True),
            notify_rapid_patterns=data.get('notify_rapid_patterns', True),
        )

        # Calculate next run time
        config.next_run_at = UserReportConfigService.calculate_next_run(
            config.frequency_value,
            config.frequency_unit
        )

        db.session.add(config)
        db.session.commit()
        return config

    @staticmethod
    def update_config(config_id, data):
        """Update an existing configuration"""
        config = UserReportConfig.query.get(config_id)
        if not config:
            raise ValueError('Configuration not found')

        # Update basic fields
        if 'name' in data:
            config.name = data['name']
        if 'description' in data:
            config.description = data['description']
        if 'report_type' in data:
            config.report_type = data['report_type']
        if 'frequency_value' in data:
            config.frequency_value = data['frequency_value']
        if 'frequency_unit' in data:
            config.frequency_unit = data['frequency_unit']
        if 'recipient_emails' in data:
            config.recipient_emails = data['recipient_emails']
        if 'is_active' in data:
            config.is_active = data['is_active']

        # Update fraud detection parameters
        if 'time_window_minutes' in data:
            config.time_window_minutes = data['time_window_minutes']
        if 'amount_variance' in data:
            config.amount_variance = data['amount_variance']
        if 'min_transactions_rollover' in data:
            config.min_transactions_rollover = data['min_transactions_rollover']
        if 'split_threshold' in data:
            config.split_threshold = data['split_threshold']
        if 'split_min_amount' in data:
            config.split_min_amount = data['split_min_amount']
        if 'split_max_amount' in data:
            config.split_max_amount = data['split_max_amount']
        if 'split_total_amount_threshold' in data:
            config.split_total_amount_threshold = data['split_total_amount_threshold']
        if 'rapid_back_forth_threshold' in data:
            config.rapid_back_forth_threshold = data['rapid_back_forth_threshold']
        if 'high_risk_score' in data:
            config.high_risk_score = data['high_risk_score']
        if 'medium_risk_score' in data:
            config.medium_risk_score = data['medium_risk_score']
        if 'analysis_period_days' in data:
            config.analysis_period_days = data['analysis_period_days']
        if 'max_transactions_per_check' in data:
            config.max_transactions_per_check = data['max_transactions_per_check']

        # Update notification settings
        if 'notify_high_risk' in data:
            config.notify_high_risk = data['notify_high_risk']
        if 'notify_medium_risk' in data:
            config.notify_medium_risk = data['notify_medium_risk']
        if 'notify_split_transactions' in data:
            config.notify_split_transactions = data['notify_split_transactions']
        if 'notify_rollover_fraud' in data:
            config.notify_rollover_fraud = data['notify_rollover_fraud']
        if 'notify_rapid_patterns' in data:
            config.notify_rapid_patterns = data['notify_rapid_patterns']

        # Recalculate next run time if frequency changed
        if 'frequency_value' in data or 'frequency_unit' in data:
            config.next_run_at = UserReportConfigService.calculate_next_run(
                config.frequency_value,
                config.frequency_unit
            )

        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config

    @staticmethod
    def delete_config(config_id):
        """Delete a configuration"""
        config = UserReportConfig.query.get(config_id)
        if not config:
            raise ValueError('Configuration not found')

        db.session.delete(config)
        db.session.commit()
        return True

    @staticmethod
    def toggle_config(config_id):
        """Toggle configuration active status"""
        config = UserReportConfig.query.get(config_id)
        if not config:
            raise ValueError('Configuration not found')

        config.is_active = not config.is_active
        if config.is_active:
            # Recalculate next run time when reactivating
            config.next_run_at = UserReportConfigService.calculate_next_run(
                config.frequency_value,
                config.frequency_unit
            )

        config.updated_at = datetime.utcnow()
        db.session.commit()
        return config

    @staticmethod
    def mark_as_run(config_id):
        """Mark a configuration as having been run"""
        config = UserReportConfig.query.get(config_id)
        if not config:
            raise ValueError('Configuration not found')

        config.last_run_at = datetime.utcnow()
        config.next_run_at = UserReportConfigService.calculate_next_run(
            config.frequency_value,
            config.frequency_unit
        )

        db.session.commit()
        return config

    @staticmethod
    def calculate_next_run(frequency_value, frequency_unit):
        """Calculate the next run time based on frequency"""
        now = datetime.utcnow()
        if frequency_unit == 'minutes':
            return now + timedelta(minutes=frequency_value)
        elif frequency_unit == 'hours':
            return now + timedelta(hours=frequency_value)
        elif frequency_unit == 'days':
            return now + timedelta(days=frequency_value)
        return now + timedelta(days=1)

    @staticmethod
    def validate_config_data(data):
        """Validate configuration data"""
        errors = []

        if not data.get('name'):
            errors.append('Configuration name is required')

        if not data.get('report_type'):
            errors.append('Report type is required')
        elif data.get('report_type') not in ['periodic_fraud', 'historical_fraud', 'daily_fraud', 'commissions']:
            errors.append('Invalid report type')

        if not data.get('frequency_value') or data.get('frequency_value') < 1:
            errors.append('Frequency value must be at least 1')

        if data.get('frequency_unit') not in ['minutes', 'hours', 'days']:
            errors.append('Invalid frequency unit')

        if not data.get('recipient_emails'):
            errors.append('At least one recipient email is required')

        # Validate fraud detection parameters (optional, only validate if provided)
        time_window = data.get('time_window_minutes')
        if time_window is not None and (time_window < 1 or time_window > 60):
            errors.append('Time window must be between 1 and 60 minutes')

        amount_variance = data.get('amount_variance')
        if amount_variance is not None and (amount_variance < 0.01 or amount_variance > 1.0):
            errors.append('Amount variance must be between 0.01 and 1.0')

        split_threshold = data.get('split_threshold')
        if split_threshold is not None and (split_threshold < 2 or split_threshold > 50):
            errors.append('Split threshold must be between 2 and 50 transactions')

        split_min = data.get('split_min_amount')
        split_max = data.get('split_max_amount')
        if split_min is not None and split_min < 0:
            errors.append('Split minimum amount cannot be negative')
        if split_max is not None and split_min is not None and split_max < split_min:
            errors.append('Split maximum amount must be greater than minimum amount')

        high_risk = data.get('high_risk_score')
        medium_risk = data.get('medium_risk_score')
        if high_risk is not None and medium_risk is not None and high_risk < medium_risk:
            errors.append('High risk score must be greater than medium risk score')

        return errors

    @staticmethod
    def get_configs_by_report_type(report_type, user_id=None):
        """Get configurations by report type, optionally filtered by user"""
        query = UserReportConfig.query.filter_by(report_type=report_type, is_active=True)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.all()
