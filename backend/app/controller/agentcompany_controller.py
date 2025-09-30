# app/controllers/ .py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from app import db
from app.model.agentcompany  import AgentCompany
from app.model.company import Company
from datetime import datetime
import pandas as pd

agent_company_bp = Blueprint('agent_company', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@agent_company_bp.route('/', methods=['GET'])
def get_agent_companies():
    try:
        agent_companies = AgentCompany.query.all()
        return jsonify([{
            'id': ac.id,
            'company_name': ac.company_name,
            'registration_number': ac.registration_number,
            'location': ac.location,
            'contact_phone': ac.contact_phone,
            'email': ac.email,
            'till_number': ac.till_number,
            'company_id': ac.company_id,
            'established_date': ac.established_date.isoformat() if ac.established_date else None,
            'float_balance': ac.float_balance,
            'status': ac.status,
            'fraud_risk_level': ac.fraud_risk_level,
            'fraud_risk_description': ac.fraud_risk_description,
            'daily_transaction_limit': ac.daily_transaction_limit,
            'commission_rate': ac.commission_rate,
            'last_audit_date': ac.last_audit_date.isoformat() if ac.last_audit_date else None
        } for ac in agent_companies]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agent_company_bp.route('/', methods=['POST'])
def create_agent_company():
    try:
        data = request.form
        company_id = data.get('company_id')
        if not Company.query.get(company_id):
            return jsonify({'error': 'Invalid company_id'}), 400

        agent_company = AgentCompany(
            company_name=data.get('company_name'),
            registration_number=data.get('registration_number'),
            location=data.get('location'),
            contact_phone=data.get('contact_phone'),
            email=data.get('email'),
            till_number=data.get('till_number'),
            company_id=company_id,
            established_date=datetime.strptime(data.get('established_date'), '%Y-%m-%d').date() if data.get('established_date') else None,
            float_balance=float(data.get('float_balance', 0.0)),
            status=data.get('status', 'active'),
            fraud_risk_level=data.get('fraud_risk_level', 'low'),
            fraud_risk_description=data.get('fraud_risk_description'),
            daily_transaction_limit=float(data.get('daily_transaction_limit', 0.0)),
            commission_rate=float(data.get('commission_rate', 0.0)),
            last_audit_date=datetime.strptime(data.get('last_audit_date'), '%Y-%m-%d').date() if data.get('last_audit_date') else None
        )
        db.session.add(agent_company)
        db.session.commit()
        return jsonify({'message': 'Agent company created successfully', 'agentCompany': {
            'id': agent_company.id,
            'company_name': agent_company.company_name,
            'registration_number': agent_company.registration_number
        }}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@agent_company_bp.route('/<int:id>', methods=['PUT'])
def update_agent_company(id):
    try:
        agent_company = AgentCompany.query.get_or_404(id)
        data = request.form
        company_id = data.get('company_id')
        if company_id and not Company.query.get(company_id):
            return jsonify({'error': 'Invalid company_id'}), 400

        agent_company.company_name = data.get('company_name', agent_company.company_name)
        agent_company.registration_number = data.get('registration_number', agent_company.registration_number)
        agent_company.location = data.get('location', agent_company.location)
        agent_company.contact_phone = data.get('contact_phone', agent_company.contact_phone)
        agent_company.email = data.get('email', agent_company.email)
        agent_company.till_number = data.get('till_number', agent_company.till_number)
        agent_company.company_id = company_id or agent_company.company_id
        agent_company.established_date = datetime.strptime(data.get('established_date'), '%Y-%m-%d').date() if data.get('established_date') else agent_company.established_date
        agent_company.float_balance = float(data.get('float_balance', agent_company.float_balance))
        agent_company.status = data.get('status', agent_company.status)
        agent_company.fraud_risk_level = data.get('fraud_risk_level', agent_company.fraud_risk_level)
        agent_company.fraud_risk_description = data.get('fraud_risk_description', agent_company.fraud_risk_description)
        agent_company.daily_transaction_limit = float(data.get('daily_transaction_limit', agent_company.daily_transaction_limit))
        agent_company.commission_rate = float(data.get('commission_rate', agent_company.commission_rate))
        agent_company.last_audit_date = datetime.strptime(data.get('last_audit_date'), '%Y-%m-%d').date() if data.get('last_audit_date') else agent_company.last_audit_date
        db.session.commit()
        return jsonify({'message': 'Agent company updated successfully', 'agentCompany': {
            'id': agent_company.id,
            'company_name': agent_company.company_name,
            'registration_number': agent_company.registration_number
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@agent_company_bp.route('/ /<int:id>', methods=['DELETE'])
def delete_agent_company(id):
    try:
        agent_company = AgentCompany.query.get_or_404(id)
        db.session.delete(agent_company)
        db.session.commit()
        return jsonify({'message': 'Agent company deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@agent_company_bp.route('/validate-batch', methods=['POST'])
def validate_batch_agent_company():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Only .xlsx allowed'}), 400

        df = pd.read_excel(file)
        required_columns = ['company_name', 'registration_number', 'location', 'company_id']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Missing required columns'}), 400

        valid_agent_companies = []
        invalid_agent_companies = []
        for index, row in df.iterrows():
            errors = []
            if not row['company_name']:
                errors.append('Company name is required')
            if not row['registration_number']:
                errors.append('Registration number is required')
            if not row['location']:
                errors.append('Location is required')
            if not pd.isna(row['company_id']) and not Company.query.get(int(row['company_id'])):
                errors.append('Invalid company_id')
            if AgentCompany.query.filter_by(registration_number=row['registration_number']).first():
                errors.append('Registration number already exists')
            if pd.notna(row['till_number']) and AgentCompany.query.filter_by(till_number=row['till_number']).first():
                errors.append('Till number already exists')

            if errors:
                invalid_agent_companies.append({'row': index + 2, 'data': row.to_dict(), 'errors': errors})
            else:
                valid_agent_companies.append(row.to_dict())

        return jsonify({
            'validAgentCompanies': valid_agent_companies,
            'invalidAgentCompanies': invalid_agent_companies
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@agent_company_bp.route('/batch', methods=['POST'])
def batch_create_agent_company():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Only .xlsx allowed'}), 400

        df = pd.read_excel(file)
        created_agent_companies = []
        for _, row in df.iterrows():
            agent_company = AgentCompany(
                company_name= row['company_name'],
                registration_number=row['registration_number'],
                location=row['location'],
                contact_phone=row.get('contact_phone'),
                email=row.get('email'),
                till_number=row.get('till_number'),
                company_id=int(row['company_id']),
                established_date=datetime.strptime(row['established_date'], '%Y-%m-%d').date() if pd.notna(row.get('established_date')) else None,
                float_balance=float(row.get('float_balance', 0.0)),
                status=row.get('status', 'active'),
                fraud_risk_level=row.get('fraud_risk_level', 'low'),
                fraud_risk_description=row.get('fraud_risk_description'),
                daily_transaction_limit=float(row.get('daily_transaction_limit', 0.0)),
                commission_rate=float(row.get('commission_rate', 0.0)),
                last_audit_date=datetime.strptime(row['last_audit_date'], '%Y-%m-%d').date() if pd.notna(row.get('last_audit_date')) else None
            )
            db.session.add(agent_company)
            created_agent_companies.append({'id': agent_company.id, 'company_name': agent_company.company_name})
        db.session.commit()
        return jsonify({
            'message': f'{len(created_agent_companies)} agent companies created successfully',
            'createdAgentCompanies': created_agent_companies
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400