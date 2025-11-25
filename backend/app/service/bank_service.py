# services/bank_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm.exc import NoResultFound
from app.model.bank_models import  Bank, BankConnectionType, BankStatus
from app.model.bank_config import BankConfig
import uuid
import json
from datetime import datetime
from app import db

class BankService:
    @staticmethod
    def get_all_banks() -> List[Bank]:
        """Get all banks with their configurations"""
        return Bank.query.all()

    @staticmethod
    def get_bank_by_id(bank_id: str) -> Optional[Bank]:
        """Get bank by ID"""
        return Bank.query.get(bank_id)

    @staticmethod
    def get_bank_by_code(bank_code: str) -> Optional[Bank]:
        """Get bank by code"""
        return Bank.query.filter_by(code=bank_code).first()

    @staticmethod
    def create_bank(bank_data: Dict[str, Any]) -> Bank:
        """Create a new bank with configuration"""
        # Validate required fields
        required_fields = ['name', 'code', 'country', 'currency', 'created_by']
        for field in required_fields:
            if not bank_data.get(field):
                raise ValueError(f"{field} is required")

        # Check if bank code already exists
        if BankService.get_bank_by_code(bank_data['code']):
            raise ValueError("Bank code already exists")

        # Create bank instance
        bank = Bank(
            id=str(uuid.uuid4()),
            name=bank_data['name'],
            code=bank_data['code'],
            country=bank_data['country'],
            currency=bank_data['currency'],
            status=BankStatus(bank_data.get('status', 'pending')),
            created_by=bank_data['created_by']
        )

        db.session.add(bank)

        # Create configuration if provided
        if bank_data.get('config'):
            BankService._create_bank_config(bank.id, bank_data['config'])

        db.session.commit()
        return bank

    @staticmethod
    def update_bank(bank_id: str, update_data: Dict[str, Any]) -> Bank:
        """Update bank and its configuration"""
        bank = BankService.get_bank_by_id(bank_id)
        if not bank:
            raise ValueError("Bank not found")

        # Update bank fields
        if 'name' in update_data:
            bank.name = update_data['name']
        if 'code' in update_data:
            # Check if new code already exists
            existing_bank = BankService.get_bank_by_code(update_data['code'])
            if existing_bank and existing_bank.id != bank_id:
                raise ValueError("Bank code already exists")
            bank.code = update_data['code']
        if 'country' in update_data:
            bank.country = update_data['country']
        if 'currency' in update_data:
            bank.currency = update_data['currency']
        if 'status' in update_data:
            bank.status = BankStatus(update_data['status'])

        bank.updated_at = datetime.utcnow()

        # Update configuration if provided
        if update_data.get('config'):
            BankService._update_bank_config(bank.id, update_data['config'])

        db.session.commit()
        return bank

    @staticmethod
    def delete_bank(bank_id: str) -> bool:
        """Delete bank and its configuration"""
        bank = BankService.get_bank_by_id(bank_id)
        if not bank:
            raise ValueError("Bank not found")

        db.session.delete(bank)
        db.session.commit()
        return True

    @staticmethod
    def _create_bank_config(bank_id: str, config_data: Dict[str, Any]) -> BankConfig:
        """Create bank configuration"""
        config = BankConfig(
            id=str(uuid.uuid4()),
            bank_id=bank_id,
            connection_type=BankConnectionType(config_data['connection_type']),
            host=config_data.get('host'),
            port=config_data.get('port'),
            username=config_data.get('username'),
            password_encrypted=config_data.get('password_encrypted'),
            api_key_encrypted=config_data.get('api_key_encrypted'),
            base_url=config_data.get('base_url'),
            sftp_directory=config_data.get('sftp_directory'),
            file_naming_convention=config_data.get('file_naming_convention'),
            supported_formats=json.dumps(config_data.get('supported_formats', [])),
            timezone=config_data.get('timezone', 'UTC'),
            retry_attempts=config_data.get('retry_attempts', 3),
            timeout_seconds=config_data.get('timeout_seconds', 30),
            additional_config=json.dumps(config_data.get('additional_config', {}))
        )
        db.session.add(config)
        return config

    @staticmethod
    def _update_bank_config(bank_id: str, config_data: Dict[str, Any]) -> BankConfig:
        """Update bank configuration"""
        bank = BankService.get_bank_by_id(bank_id)
        if not bank:
            raise ValueError("Bank not found")

        if bank.config:
            config = bank.config
        else:
            config = BankConfig(id=str(uuid.uuid4()), bank_id=bank_id)
            db.session.add(config)

        # Update config fields
        if 'connection_type' in config_data:
            config.connection_type = BankConnectionType(config_data['connection_type'])
        if 'host' in config_data:
            config.host = config_data['host']
        if 'port' in config_data:
            config.port = config_data['port']
        if 'username' in config_data:
            config.username = config_data['username']
        if 'password_encrypted' in config_data:
            config.password_encrypted = config_data['password_encrypted']
        if 'api_key_encrypted' in config_data:
            config.api_key_encrypted = config_data['api_key_encrypted']
        if 'base_url' in config_data:
            config.base_url = config_data['base_url']
        if 'sftp_directory' in config_data:
            config.sftp_directory = config_data['sftp_directory']
        if 'file_naming_convention' in config_data:
            config.file_naming_convention = config_data['file_naming_convention']
        if 'supported_formats' in config_data:
            config.supported_formats = json.dumps(config_data['supported_formats'])
        if 'timezone' in config_data:
            config.timezone = config_data['timezone']
        if 'retry_attempts' in config_data:
            config.retry_attempts = config_data['retry_attempts']
        if 'timeout_seconds' in config_data:
            config.timeout_seconds = config_data['timeout_seconds']
        if 'additional_config' in config_data:
            config.additional_config = json.dumps(config_data['additional_config'])

        return config

    @staticmethod
    def search_banks(search_term: str) -> List[Bank]:
        """Search banks by name, code, or country"""
        return Bank.query.filter(
            (Bank.name.ilike(f'%{search_term}%')) |
            (Bank.code.ilike(f'%{search_term}%')) |
            (Bank.country.ilike(f'%{search_term}%'))
        ).all()

    @staticmethod
    def get_banks_by_status(status: BankStatus) -> List[Bank]:
        """Get banks by status"""
        return Bank.query.filter_by(status=status).all()

    @staticmethod
    def get_banks_by_connection_type(connection_type: BankConnectionType) -> List[Bank]:
        """Get banks by connection type"""
        return Bank.query.join(BankConfig).filter(
            BankConfig.connection_type == connection_type
        ).all()

    @staticmethod
    def test_bank_connection(bank_id: str) -> Dict[str, Any]:
        """Test bank connection (simulated)"""
        bank = BankService.get_bank_by_id(bank_id)
        if not bank:
            raise ValueError("Bank not found")

        # Simulate connection test
        # In real implementation, this would test actual connection
        # based on the connection type and configuration
        
        connection_success = bool(bank.config and bank.config.host)
        
        return {
            'success': connection_success,
            'message': 'Connection test successful' if connection_success else 'Connection test failed',
            'bank_id': bank_id,
            'connection_type': bank.config.connection_type.value if bank.config else None,
            'tested_at': datetime.utcnow().isoformat()
        }