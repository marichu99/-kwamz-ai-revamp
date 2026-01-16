from flask import Blueprint, request, jsonify, render_template
from app.service.config_service import ConfigService as CS
from app import db
import json

config_bp = Blueprint('config', __name__, url_prefix='/config')

@config_bp.route('/', methods=['GET'])
def get_all_configs():
    """Get all configurations"""
    configs = CS.get_all_configs()
    return jsonify({
        'success': True,
        'data': [config.to_dict() for config in configs]
    })

@config_bp.route('/active', methods=['GET'])
def get_active_config():
    """Get active configuration"""
    config = CS.get_active_config()
    if config:
        return jsonify({
            'success': True,
            'data': config.to_dict()
        })
    return jsonify({
        'success': False,
        'message': 'No active configuration found'
    }), 404

@config_bp.route('/', methods=['POST'])
def create_config():
    """Create new configuration"""
    try:
        data = request.get_json()
        
        # Validate data
        errors = CS.validate_config_data(data)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Create config
        created_by = request.headers.get('X-User-Id', 'system')
        config = CS.create_config(data, created_by)
        
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
def get_config(config_id):
    """Get configuration by ID"""
    config = CS.get_config_by_id(config_id)
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
def update_config(config_id):
    """Update configuration"""
    try:
        data = request.get_json()
        
        # Validate data
        errors = CS.validate_config_data(data)
        if errors:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Update config
        config = CS.update_config(config_id, data)
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully',
            'data': config.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@config_bp.route('/<int:config_id>', methods=['DELETE'])
def delete_config(config_id):
    """Delete configuration"""
    try:
        CS.delete_config(config_id)
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
def activate_config(config_id):
    """Activate configuration"""
    try:
        config = CS.activate_config(config_id)
        return jsonify({
            'success': True,
            'message': 'Configuration activated successfully',
            'data': config.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400