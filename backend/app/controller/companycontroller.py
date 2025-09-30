# app/controllers/company.py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from app import db
from app.model.company import Company
import pandas as pd

company_bp = Blueprint('company', __name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@company_bp.route('/company', methods=['GET'])
def get_companies():
    try:
        companies = Company.query.all()
        return jsonify([{
            'id': c.id,
            'company_name': c.company_name,
            'registration_number': c.registration_number,
            'address': c.address,
            'primary_owner_name': c.primary_owner_name,
            'primary_owner_id': c.primary_owner_id,
            'file_location': c.file_location,
            'compliance_status': c.compliance_status,
            'total_float_balance': c.total_float_balance
        } for c in companies]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@company_bp.route('/company', methods=['POST'])
def create_company():
    try:
        data = request.form
        file = request.files.get('file')
        file_location = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            file_location = file_path

        company = Company(
            company_name=data.get('company_name'),
            registration_number=data.get('registration_number'),
            address=data.get('address'),
            primary_owner_name=data.get('primary_owner_name'),
            primary_owner_id=data.get('primary_owner_id'),
            file_location=file_location,
            compliance_status=data.get('compliance_status', 'under_review'),
            total_float_balance=float(data.get('total_float_balance', 0.0))
        )
        db.session.add(company)
        db.session.commit()
        return jsonify({'message': 'Company created successfully', 'company': {
            'id': company.id,
            'company_name': company.company_name,
            'registration_number': company.registration_number
        }}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@company_bp.route('/company/<int:id>', methods=['PUT'])
def update_company(id):
    try:
        company = Company.query.get_or_404(id)
        data = request.form
        file = request.files.get('file')
        file_location = company.file_location
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            file_location = file_path

        company.company_name = data.get('company_name', company.company_name)
        company.registration_number = data.get('registration_number', company.registration_number)
        company.address = data.get('address', company.address)
        company.primary_owner_name = data.get('primary_owner_name', company.primary_owner_name)
        company.primary_owner_id = data.get('primary_owner_id', company.primary_owner_id)
        company.file_location = file_location
        company.compliance_status = data.get('compliance_status', company.compliance_status)
        company.total_float_balance = float(data.get('total_float_balance', company.total_float_balance))
        db.session.commit()
        return jsonify({'message': 'Company updated successfully', 'company': {
            'id': company.id,
            'company_name': company.company_name,
            'registration_number': company.registration_number
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@company_bp.route('/company/<int:id>', methods=['DELETE'])
def delete_company(id):
    try:
        company = Company.query.get_or_404(id)
        db.session.delete(company)
        db.session.commit()
        return jsonify({'message': 'Company deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@company_bp.route('/company/validate-batch', methods=['POST'])
def validate_batch_company():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Only .xlsx allowed'}), 400

        df = pd.read_excel(file)
        required_columns = ['company_name', 'registration_number', 'address', 'primary_owner_name', 'primary_owner_id']
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Missing required columns'}), 400

        valid_companies = []
        invalid_companies = []
        for index, row in df.iterrows():
            errors = []
            if not row['company_name']:
                errors.append('Company name is required')
            if not row['registration_number']:
                errors.append('Registration number is required')
            if not row['address']:
                errors.append('Address is required')
            if not row['primary_owner_name']:
                errors.append('Primary owner name is required')
            if not row['primary_owner_id']:
                errors.append('Primary owner ID is required')
            if Company.query.filter_by(registration_number=row['registration_number']).first():
                errors.append('Registration number already exists')

            if errors:
                invalid_companies.append({'row': index + 2, 'data': row.to_dict(), 'errors': errors})
            else:
                valid_companies.append(row.to_dict())

        return jsonify({
            'validCompanies': valid_companies,
            'invalidCompanies': invalid_companies
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@company_bp.route('/company/batch', methods=['POST'])
def batch_create_company():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Only .xlsx allowed'}), 400

        df = pd.read_excel(file)
        created_companies = []
        for _, row in df.iterrows():
            company = Company(
                company_name=row['company_name'],
                registration_number=row['registration_number'],
                address=row['address'],
                primary_owner_name=row['primary_owner_name'],
                primary_owner_id=row['primary_owner_id'],
                compliance_status=row.get('compliance_status', 'under_review'),
                total_float_balance=float(row.get('total_float_balance', 0.0))
            )
            db.session.add(company)
            created_companies.append({'id': company.id, 'company_name': company.company_name})
        db.session.commit()
        return jsonify({
            'message': f'{len(created_companies)} companies created successfully',
            'createdCompanies': created_companies
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400