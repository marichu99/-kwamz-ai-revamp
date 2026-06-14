import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.service.user_report_config_service import UserReportConfigService

logger = logging.getLogger(__name__)

user_report_config_bp = Bluelogger.info('user_report_config', __name__, url_prefix='/api/user-report-config')


@user_report_config_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_configs():
    """Get all report configurations for the current user"""
    try:
        current_user_id = get_jwt_identity()
        # Ensure user_id is an integer for comparison
        current_user_id = int(current_user_id) if current_user_id else None
        configs = UserReportConfigService.get_all_configs_for_user(current_user_id)
        return jsonify({
            'success': True,
            'data': [config.to_dict() for config in configs]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@user_report_config_bp.route('/<int:config_id>', methods=['GET'])
@jwt_required()
def get_config(config_id):
    """Get a specific configuration by ID"""
    try:
        current_user_id = get_jwt_identity()
        # Ensure user_id is an integer for comparison
        current_user_id = int(current_user_id) if current_user_id else None
        config = UserReportConfigService.get_config_by_id(config_id)

        if not config:
            return jsonify({
                'success': False,
                'message': 'Configuration not found'
            }), 404

        # Ensure the config belongs to the current user
        if config.user_id != current_user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access to this configuration'
            }), 403

        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@user_report_config_bp.route('/', methods=['POST'])
@jwt_required()
def create_config():
    """Create a new report configuration"""
    try:
        current_user_id = get_jwt_identity()
        # Ensure user_id is an integer
        current_user_id = int(current_user_id) if current_user_id else None
        data = request.get_json()

        # Validate data
        errors = UserReportConfigService.validate_config_data(data)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400

        # Create config
        config = UserReportConfigService.create_config(data, current_user_id)

        return jsonify({
            'success': True,
            'message': 'Report configuration created successfully',
            'data': config.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@user_report_config_bp.route('/<int:config_id>', methods=['PUT'])
@jwt_required()
def update_config(config_id):
    """Update an existing configuration"""
    try:
        current_user_id = get_jwt_identity()
        # Ensure user_id is an integer for comparison
        current_user_id = int(current_user_id) if current_user_id else None
        data = request.get_json()

        # Check if config exists and belongs to user
        existing_config = UserReportConfigService.get_config_by_id(config_id)
        if not existing_config:
            return jsonify({
                'success': False,
                'message': 'Configuration not found'
            }), 404

        if existing_config.user_id != current_user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access to this configuration'
            }), 403

        # Validate data
        errors = UserReportConfigService.validate_config_data(data)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400

        # Update config
        config = UserReportConfigService.update_config(config_id, data)

        return jsonify({
            'success': True,
            'message': 'Report configuration updated successfully',
            'data': config.to_dict()
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@user_report_config_bp.route('/<int:config_id>', methods=['DELETE'])
@jwt_required()
def delete_config(config_id):
    """Delete a configuration"""
    try:
        current_user_id = get_jwt_identity()
        # Ensure user_id is an integer for comparison
        current_user_id = int(current_user_id) if current_user_id else None

        # Check if config exists and belongs to user
        existing_config = UserReportConfigService.get_config_by_id(config_id)
        if not existing_config:
            return jsonify({
                'success': False,
                'message': 'Configuration not found'
            }), 404

        if existing_config.user_id != current_user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access to this configuration'
            }), 403

        UserReportConfigService.delete_config(config_id)

        return jsonify({
            'success': True,
            'message': 'Report configuration deleted successfully'
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@user_report_config_bp.route('/<int:config_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_config(config_id):
    """Toggle configuration active status"""
    try:
        current_user_id = get_jwt_identity()
        # Ensure user_id is an integer for comparison
        current_user_id = int(current_user_id) if current_user_id else None

        # Check if config exists and belongs to user
        existing_config = UserReportConfigService.get_config_by_id(config_id)
        if not existing_config:
            return jsonify({
                'success': False,
                'message': 'Configuration not found'
            }), 404

        if existing_config.user_id != current_user_id:
            return jsonify({
                'success': False,
                'message': 'Unauthorized access to this configuration'
            }), 403

        config = UserReportConfigService.toggle_config(config_id)

        return jsonify({
            'success': True,
            'message': f'Configuration {"activated" if config.is_active else "deactivated"} successfully',
            'data': config.to_dict()
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@user_report_config_bp.route('/report-types', methods=['GET'])
@jwt_required()
def get_report_types():
    """Get available report types"""
    report_types = [
        {'value': 'periodic_fraud', 'label': 'Periodic Fraud Report', 'description': 'Regular fraud detection reports at specified intervals'},
        {'value': 'historical_fraud', 'label': 'Historical Fraud Report', 'description': 'Analysis of historical fraud patterns over time'},
        {'value': 'daily_fraud', 'label': 'Daily Fraud Report', 'description': 'Daily summary of fraud detection results'},
        {'value': 'commissions', 'label': 'Commissions Report', 'description': 'Agent commission calculations and summaries'}
    ]
    return jsonify({
        'success': True,
        'data': report_types
    })


@user_report_config_bp.route('/frequency-units', methods=['GET'])
@jwt_required()
def get_frequency_units():
    """Get available frequency units"""
    frequency_units = [
        {'value': 'minutes', 'label': 'Minutes', 'min': 5, 'max': 59},
        {'value': 'hours', 'label': 'Hours', 'min': 1, 'max': 23},
        {'value': 'days', 'label': 'Days', 'min': 1, 'max': 30}
    ]
    return jsonify({
        'success': True,
        'data': frequency_units
    })


@user_report_config_bp.route('/default-detection-params', methods=['GET'])
@jwt_required()
def get_default_detection_params():
    """Get default fraud detection parameters for form initialization"""
    default_params = {
        # Detection Parameters
        'time_window_minutes': {'value': 5, 'min': 1, 'max': 60, 'label': 'Time Window (minutes)', 'description': 'Time window for detecting patterns'},
        'amount_variance': {'value': 0.1, 'min': 0.01, 'max': 1.0, 'label': 'Amount Variance', 'description': 'Tolerance for similar amounts (0.1 = 10%)'},
        'min_transactions_rollover': {'value': 3, 'min': 2, 'max': 20, 'label': 'Min Transactions (Rollover)', 'description': 'Minimum transactions for rollover detection'},

        # Split Transaction Thresholds
        'split_threshold': {'value': 5, 'min': 2, 'max': 50, 'label': 'Split Threshold', 'description': 'Min transactions to flag as split'},
        'split_min_amount': {'value': 100.0, 'min': 0, 'max': 100000, 'label': 'Split Min Amount (KES)', 'description': 'Minimum amount per transaction'},
        'split_max_amount': {'value': 50000.0, 'min': 0, 'max': 1000000, 'label': 'Split Max Amount (KES)', 'description': 'Maximum amount per transaction'},
        'split_total_amount_threshold': {'value': 10000.0, 'min': 0, 'max': 1000000, 'label': 'Split Total Threshold (KES)', 'description': 'Total amount threshold for suspicion'},

        # Other Detection
        'rapid_back_forth_threshold': {'value': 2, 'min': 1, 'max': 10, 'label': 'Rapid Pattern Threshold', 'description': 'Threshold for rapid back-forth detection'},

        # Risk Scores
        'high_risk_score': {'value': 50, 'min': 1, 'max': 100, 'label': 'High Risk Score', 'description': 'Score threshold for high risk'},
        'medium_risk_score': {'value': 30, 'min': 1, 'max': 100, 'label': 'Medium Risk Score', 'description': 'Score threshold for medium risk'},

        # Analysis Settings
        'analysis_period_days': {'value': 30, 'min': 1, 'max': 365, 'label': 'Analysis Period (days)', 'description': 'Days to analyze for historical reports'},
        'max_transactions_per_check': {'value': 100, 'min': 10, 'max': 1000, 'label': 'Max Transactions per Check', 'description': 'Maximum transactions per shortcode'},

        # Notification Settings
        'notify_high_risk': {'value': True, 'label': 'Notify High Risk', 'description': 'Send notifications for high risk alerts'},
        'notify_medium_risk': {'value': False, 'label': 'Notify Medium Risk', 'description': 'Send notifications for medium risk alerts'},
        'notify_split_transactions': {'value': True, 'label': 'Notify Split Transactions', 'description': 'Send notifications for split transaction fraud'},
        'notify_rollover_fraud': {'value': True, 'label': 'Notify Rollover Fraud', 'description': 'Send notifications for rollover fraud'},
        'notify_rapid_patterns': {'value': True, 'label': 'Notify Rapid Patterns', 'description': 'Send notifications for rapid back-forth patterns'},
    }
    return jsonify({
        'success': True,
        'data': default_params
    })
