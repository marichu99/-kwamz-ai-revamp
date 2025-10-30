from typing import Optional, Dict, List
from datetime import datetime
from app import db
from app.model.pesapalipnconfig import PesapalIPNConfig

class FlaskIPNStorage:
    """Flask-SQLAlchemy implementation of IPNStorage"""
    
    def get_ipn_config(self, url: str) -> Optional[Dict]:
        try:
            config = PesapalIPNConfig.query.filter_by(
                ipn_url=url, 
                is_active=True
            ).first()
            
            if config:
                return {
                    'ipn_url': config.ipn_url,
                    'notification_id': config.notification_id,
                    'environment': config.environment,
                    'ipn_notification_type': config.ipn_notification_type,
                    'response_data': config.response_data,
                    'created_at': config.created_at.isoformat(),
                    'updated_at': config.updated_at.isoformat()
                }
        except Exception as e:
            print(f"Error retrieving IPN config: {e}")
        return None
    
    def save_ipn_config(self, url: str, notification_id: str, response_data: Dict) -> None:
        import os
        environment = os.getenv('PESAPAL_ENVIRONMENT', 'SANDBOX')
        
        config = PesapalIPNConfig.query.filter_by(ipn_url=url).first()
        
        if config:
            config.notification_id = notification_id
            config.environment = environment
            config.response_data = response_data
            config.is_active = True
            config.updated_at = datetime.utcnow()
        else:
            config = PesapalIPNConfig(
                ipn_url=url,
                notification_id=notification_id,
                environment=environment,
                response_data=response_data,
                is_active=True
            )
            db.session.add(config)
        
        db.session.commit()
    
    def list_ipn_configs(self) -> List[Dict]:
        configs = PesapalIPNConfig.query.filter_by(is_active=True).all()
        return [config.to_dict() for config in configs]

