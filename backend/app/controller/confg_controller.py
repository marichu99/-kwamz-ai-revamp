from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.service.config_service import ConfigService as CS
from app.model.user import User
from app.model.config import SmtpConfig
from app import db

config_bp = Blueprint('config', __name__)

@config_bp.route('/fraud-types', methods=['GET'])
@jwt_required()
def get_fraud_types():
    """Get fraud type metadata (names, descriptions, parameters, defaults)"""
    return jsonify({
        'success': True,
        'data': CS.get_fraud_type_info()
    })

@config_bp.route('', methods=['GET'])
@config_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_configs():
    """Get all configurations for the authenticated user"""
    user_id = get_jwt_identity()
    configs = CS.get_all_configs(user_id)
    return jsonify({
        'success': True,
        'data': [config.to_dict() for config in configs]
    })

@config_bp.route('/active', methods=['GET'])
@jwt_required()
def get_active_config():
    """Get active configuration for the authenticated user"""
    user_id = get_jwt_identity()
    config = CS.get_active_config(user_id)
    if config:
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    return jsonify({
        'success': False,
        'message': 'No active configuration found'
    }), 404

@config_bp.route('', methods=['POST'])
@config_bp.route('/', methods=['POST'])
@jwt_required()
def create_config():
    """Create new configuration for the authenticated user"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Validate data
        errors = CS.validate_config_data(data)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400

        # Create config
        config = CS.create_config(data, user_id, created_by=str(user_id))

        return jsonify({
            'success': True,
            'message': 'Configuration created successfully',
            'data': config.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@config_bp.route('/<int:config_id>', methods=['GET'])
@jwt_required()
def get_config(config_id):
    """Get configuration by ID for the authenticated user"""
    user_id = get_jwt_identity()
    config = CS.get_config_by_id(config_id, user_id)
    if config:
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    return jsonify({
        'success': False,
        'message': 'Configuration not found'
    }), 404

@config_bp.route('/<int:config_id>', methods=['PUT'])
@jwt_required()
def update_config(config_id):
    """Update configuration for the authenticated user"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Validate data
        errors = CS.validate_config_data(data)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400

        # Update config (ownership verified inside service)
        config = CS.update_config(config_id, user_id, data)

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
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

@config_bp.route('/<int:config_id>', methods=['DELETE'])
@jwt_required()
def delete_config(config_id):
    """Delete configuration for the authenticated user"""
    try:
        user_id = get_jwt_identity()
        CS.delete_config(config_id, user_id)
        return jsonify({
            'success': True,
            'message': 'Configuration deleted successfully'
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'Configuration not found'
        }), 404

@config_bp.route('/<int:config_id>/activate', methods=['POST'])
@jwt_required()
def activate_config(config_id):
    """Activate configuration for the authenticated user"""
    try:
        user_id = get_jwt_identity()
        config = CS.activate_config(config_id, user_id)
        return jsonify({
            'success': True,
            'message': 'Configuration activated successfully',
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


@config_bp.route('/smtp', methods=['GET'])
@jwt_required()
def get_smtp_config():
    """Get global SMTP configuration (admin only)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    smtp = SmtpConfig.get_global()
    return jsonify({'success': True, 'data': smtp.to_dict()})


@config_bp.route('/smtp', methods=['PUT'])
@jwt_required()
def update_smtp_config():
    """Update global SMTP configuration (admin only)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or user.role != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    data = request.get_json()
    smtp = SmtpConfig.get_global()
    smtp.from_dict(data)
    smtp.updated_by = user_id
    db.session.commit()
    return jsonify({'success': True, 'message': 'SMTP configuration updated', 'data': smtp.to_dict()})
