from flask import Blueprint, request, jsonify, current_app
from app.service.config_service import DetectionService, ConfigService
from app.service.fraud_detector import FraudDetectionSystem
import json
from datetime import datetime
import pandas as pd

detection_bp = Blueprint('detection', __name__, url_prefix='/api/detection')

@detection_bp.route('/run', methods=['POST'])
def run_detection():
    """Run fraud detection"""
    try:
        data = request.get_json()
        transaction_data = data.get('transaction_data')
        config_id = data.get('config_id')
        initiated_by = request.headers.get('X-User-Id', 'system')
        
        if not transaction_data:
            return jsonify({
                'success': False,
                'message': 'Transaction data is required'
            }), 400
        
        # Get configuration
        if config_id:
            config = ConfigService.get_config_by_id(config_id)
            if not config:
                return jsonify({
                    'success': False,
                    'message': 'Configuration not found'
                }), 404
        else:
            config = ConfigService.get_active_config()
            if not config:
                return jsonify({
                    'success': False,
                    'message': 'No active configuration found'
                }), 404
        
        # Create detection log
        detection_log = DetectionService.create_detection_log(
            config.id, 
            initiated_by
        )
        
        try:
            # Initialize fraud detector
            detector = FraudDetectionSystem(config.to_dict())
            
            # Run detection
            results, report = detector.detect_all_fraud(transaction_data)
            
            # Update detection log
            DetectionService.update_detection_log(detection_log.id, {
                'status': 'completed',
                'completed_at': datetime.utcnow(),
                'total_transactions': report['summary']['total_transactions'],
                'flagged_transactions': report['summary']['flagged_transactions'],
                'split_cases': report['summary']['split_cases'],
                'rollover_cases': report['summary']['rollover_cases'],
                'rapid_cases': report['summary']['rapid_cases'],
                'high_risk_count': report['summary']['high_risk_count'],
                'log_messages': 'Detection completed successfully'
            })
            
            # Save suspicious accounts
            if not report['account_summary'].empty:
                accounts_data = []
                for (phone, name), row in report['account_summary'].iterrows():
                    accounts_data.append({
                        'phone_number': phone if not pd.isna(phone) else 'Unknown',
                        'account_name': name if not pd.isna(name) else '',
                        'fraud_score': float(row['Fraud Score']),
                        'risk_level': row['Risk Level'],
                        'suspicious_transactions': int(row['Receipt No.']),
                        'total_amount': float(row['Absolute Amount']),
                        'split_detected': False,  # You can refine this
                        'rollover_detected': False,
                        'rapid_detected': False
                    })
                
                DetectionService.save_suspicious_accounts(detection_log.id, accounts_data)
            
            return jsonify({
                'success': True,
                'message': 'Fraud detection completed successfully',
                'data': {
                    'detection_log': detection_log.to_dict(),
                    'summary': report['summary'],
                    'suspicious_accounts_count': len(accounts_data) if 'accounts_data' in locals() else 0
                }
            })
            
        except Exception as e:
            # Update log with failure
            DetectionService.update_detection_log(detection_log.id, {
                'status': 'failed',
                'completed_at': datetime.utcnow(),
                'log_messages': f'Detection failed: {str(e)}'
            })
            
            return jsonify({
                'success': False,
                'message': f'Fraud detection failed: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@detection_bp.route('/logs', methods=['GET'])
def get_detection_logs():
    """Get detection logs"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    logs = DetectionService.get_detection_logs(page, per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'logs': [log.to_dict() for log in logs.items],
            'total': logs.total,
            'pages': logs.pages,
            'current_page': logs.page,
            'per_page': logs.per_page
        }
    })

@detection_bp.route('/logs/<int:log_id>', methods=['GET'])
def get_detection_log(log_id):
    """Get specific detection log"""
    log = DetectionService.get_detection_log_by_id(log_id)
    
    # Get suspicious accounts for this log
    suspicious_accounts = [acc.to_dict() for acc in log.suspicious_accounts]
    
    return jsonify({
        'success': True,
        'data': {
            'log': log.to_dict(),
            'suspicious_accounts': suspicious_accounts
        }
    })