from flask import Blueprint, request, jsonify
from app import db
from app.service.company_service import CompanyService
from app.model.agentcompany import AgentCompany
from app.model.user import User
from app.model.pesalpalpayment import PesapalPayment
from app.model.company import Company
from app.model.agent_documents import AgentDocuments
from flask_jwt_extended import jwt_required,get_jwt_identity
from app.model.mpesa_scrape_job import MpesaScrapeJob
from decimal import Decimal, InvalidOperation
from datetime import datetime
import json


company_bp = Blueprint('company', __name__, url_prefix='/company')

company_service = CompanyService(db)


# Handle OPTIONS requests separately
@company_bp.route('', methods=['OPTIONS'])
@company_bp.route('/', methods=['OPTIONS'])
def handle_options():
    return jsonify({'message': 'OK'}), 200

@company_bp.route('/', methods=['GET'])
@company_bp.route('', methods=['GET'])
@jwt_required()
def get_companies():
    user_id = get_jwt_identity()
    user = User.query.get_or_404(user_id)  
    
    if user.role is not None and user.role.lower() == 'admin':
        companies, error = company_service.get_companies()
    else:
        companies, error = company_service.get_companies_by_userid(user_id=user_id)
        
    if error:
        return jsonify({'error': error}), 500
    return jsonify(companies), 200

@company_bp.route('/', methods=['POST', 'OPTIONS'])
@company_bp.route('', methods=['POST', 'OPTIONS'])
@company_bp.route('/<int:company_id>', methods=['PUT'])
@jwt_required()
def create_or_update_company(company_id=None):
    try:
        data = request.form.to_dict()
        file = request.files.get('cr12_file')
        current_user_id = get_jwt_identity()
        
        if file:
            data['cr12_file'] = file
        
        print(f"Raw form data: {data}")  # Debug log
        data["user_id"]=current_user_id
        
        # Parse JSON strings for arrays
        if 'secondary_shareholders' in data:
            try:
                data['secondary_shareholders'] = json.loads(data['secondary_shareholders'])
                print(f"Parsed secondary_shareholders: {data['secondary_shareholders']}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse secondary_shareholders JSON: {e}")
                data['secondary_shareholders'] = []
        
        if 'directors' in data:
            try:
                data['directors'] = json.loads(data['directors'])
                print(f"Parsed directors: {data['directors']}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse directors JSON: {e}")
                data['directors'] = []
        
        # Convert numeric fields
        if 'primary_owner_shares' in data:
            try:
                data['primary_owner_shares'] = float(data['primary_owner_shares'])
            except (ValueError, TypeError):
                data['primary_owner_shares'] = 0.0
        
        print(f"Processed data for service: {data}")  # Debug log
        
        if company_id:
            # Update existing company
            company_id, message = company_service.update_company(company_id, data)
        else:
            # Create new company
            company_id, message = company_service.onboard_company(data)
            
        if company_id is None:
            return jsonify({'error': message}), 400
            
        return jsonify({'id': company_id, 'message': message, 'company': {'id': company_id}}), 201 if not company_id else 200
        
    except Exception as e:
        print(f"Error in create_or_update_company route: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to {"update" if company_id else "create"} company: {str(e)}'}), 500

@company_bp.route('/company/<int:id>', methods=['PUT'])
def update_company(id):
    try:
        data = request.form.to_dict()
        file = request.files.get('file')
        
        # Parse JSON fields from form data
        json_fields = ['secondary_shareholders', 'directors']
        for field in json_fields:
            if field in data and data[field]:
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    return jsonify({'error': f'Invalid {field} JSON format'}), 400
        
        # Handle registration_date conversion
        if 'registration_date' in data and data['registration_date']:
            try:
                data['registration_date'] = datetime.strptime(data['registration_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid registration_date format. Use YYYY-MM-DD'}), 400
        
        # Convert numeric fields
        numeric_fields = ['primary_owner_shares', 'total_float_balance']
        for field in numeric_fields:
            if field in data and data[field]:
                try:
                    data[field] = Decimal(str(data[field]))
                except (ValueError, InvalidOperation):
                    return jsonify({'error': f'Invalid {field} value'}), 400
        
        result, error = company_service.update_company(id, data, file)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'message': 'Company updated successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@company_bp.route('/agent-payments', methods=['GET'])
def get_agent_payments():
    # try:
    # Get all companies with agent_user_id
    companies_with_agents = Company.query.filter(Company.agent_user_id.isnot(None)).all()
    
    # Group companies by agent_user_id
    agents_data = {}
    
    for company in companies_with_agents:
        agent_user_id = company.agent_user_id
        
        if agent_user_id not in agents_data:
            # Get agent user details
            agent_user = User.query.get(agent_user_id)
            agents_data[agent_user_id] = {
                'agent_user_id': agent_user_id,
                'agent_name': f"{agent_user.firstname} {agent_user.lastname}" if agent_user.firstname and agent_user.lastname else agent_user.username,
                'agent_email': agent_user.email,
                'agent_phone': agent_user.phone_number,
                'total_payments_count': 0,
                'total_payments_amount': 0,
                'companies': []
            }
        
        # Get Pesapal payments for this company initiated by the agent
        company_payments = PesapalPayment.query.filter_by(
            user_id=agent_user_id
        ).all()
        
        # Alternative: If you have a direct company_id in PesapalPayment, use:
        # company_payments = PesapalPayment.query.filter_by(
        #     user_id=agent_user_id,
        #     company_id=company.id  # If you add this field to PesapalPayment
        # ).all()
        
        company_data = {
            'id': company.id,
            'company_name': company.company_name,
            'registration_number': company.registration_number,
            'address': company.address,
            'company_code': company.company_code,
            'compliance_status': company.compliance_status,
            'total_payments_count': len(company_payments),
            'total_payments_amount': sum(payment.amount for payment in company_payments),
            'payments': []
        }
        
        for payment in company_payments:
            payment_data = {
                'id': payment.id,
                'merchant_reference': payment.merchant_reference,
                'order_tracking_id': payment.order_tracking_id,
                'confirmation_code': payment.confirmation_code,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'description': payment.description,
                'customer_email': payment.customer_email,
                'customer_phone': payment.customer_phone,
                'customer_first_name': payment.customer_first_name,
                'customer_last_name': payment.customer_last_name,
                'payment_status': payment.payment_status,
                'payment_method': payment.payment_method,
                'status_code': payment.status_code,
                'payment_status_description': payment.payment_status_description,
                'created_at': payment.created_at.isoformat() if payment.created_at else None,
                'updated_at': payment.updated_at.isoformat() if payment.updated_at else None,
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
                'error_message': payment.error_message,
                'callback_data': payment.callback_data,
                'ipn_data': payment.ipn_data
            }
            company_data['payments'].append(payment_data)
        
        agents_data[agent_user_id]['companies'].append(company_data)
        agents_data[agent_user_id]['total_payments_count'] += len(company_payments)
        agents_data[agent_user_id]['total_payments_amount'] += sum(payment.amount for payment in company_payments)
    
    # Convert to list
    result = list(agents_data.values())
    
    return jsonify({
        'success': True,
        'data': result,
        'total_agents': len(result),
        'timestamp': datetime.utcnow().isoformat()
    })
        
    # except Exception as e:
    #     return jsonify({
    #         'success': False,
    #         'error': str(e),
    #         'data': []
    #     }), 500

@company_bp.route('/login-company', methods=['POST'])
@jwt_required()
def login_company():
    form_data = request.get_json()
    current_user_id = get_jwt_identity()
    short_code = form_data.get('shortCode')
    user_name = form_data.get('userName')
    password = form_data.get('password')

    if not all([short_code, user_name, password]):
        return jsonify({"success": False, "message": "shortCode, userName, and password are required"}), 400

    job = MpesaScrapeJob(
        user_id=current_user_id,
        short_code=short_code,
        username=user_name,
        password=password,
        status='pending',
    )
    db.session.add(job)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Scraping job queued. The desktop agent will process it shortly.",
        "job_id": job.id,
    })

# Alternative route if you want to add company_id to PesapalPayment model
@company_bp.route('/agent-payments-direct', methods=['GET'])
def get_agent_payments_direct():
    try:
        # This version assumes you add company_id to PesapalPayment model
        agents_data = {}
        
        # Get all Pesapal payments with company relationships
        payments_with_companies = db.session.query(
            PesapalPayment, Company
        ).join(
            Company, PesapalPayment.company_id == Company.id
        ).filter(
            Company.agent_user_id.isnot(None)
        ).all()
        
        for payment, company in payments_with_companies:
            agent_user_id = company.agent_user_id
            
            if agent_user_id not in agents_data:
                agent_user = User.query.get(agent_user_id)
                agents_data[agent_user_id] = {
                    'agent_user_id': agent_user_id,
                    'agent_name': f"{agent_user.firstname} {agent_user.lastname}" if agent_user.firstname and agent_user.lastname else agent_user.username,
                    'agent_email': agent_user.email,
                    'agent_phone': agent_user.phone_number,
                    'total_payments_count': 0,
                    'total_payments_amount': 0,
                    'companies': {}
                }
            
            agent_data = agents_data[agent_user_id]
            
            # Initialize company data if not exists
            if company.id not in agent_data['companies']:
                agent_data['companies'][company.id] = {
                    'id': company.id,
                    'company_name': company.company_name,
                    'registration_number': company.registration_number,
                    'address': company.address,
                    'company_code': company.company_code,
                    'compliance_status': company.compliance_status,
                    'total_payments_count': 0,
                    'total_payments_amount': 0,
                    'payments': []
                }
            
            company_data = agent_data['companies'][company.id]
            
            # Add payment data
            payment_data = payment.to_dict()
            company_data['payments'].append(payment_data)
            company_data['total_payments_count'] += 1
            company_data['total_payments_amount'] += payment.amount
            
            # Update agent totals
            agent_data['total_payments_count'] += 1
            agent_data['total_payments_amount'] += payment.amount
        
        # Convert to desired format
        result = []
        for agent_id, agent_data in agents_data.items():
            agent_data['companies'] = list(agent_data['companies'].values())
            result.append(agent_data)
        
        return jsonify({
            'success': True,
            'data': result,
            'total_agents': len(result)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@company_bp.route('/company-hierarchy', methods=['GET'])
@jwt_required()
def get_company_hierarchy():
    """
    Get hierarchical report: Company -> AgentCompany -> UserAgents
    """
    try:
        # Query all companies with their relationships
        companies = Company.query.all()
        
        hierarchy = []
        
        for company in companies:
            print(f"Processing company: {company.company_name}")
            print(f"Processing company: {company.id}")
            # Get all agent companies for this company
            agent_companies = AgentCompany.query.filter_by(company_id=company.id).all()
            
            agent_companies_data = []
            total_agents = 0
            
            for agent_company in agent_companies:
                # Get all user agents for this agent company
                user_agents = agent_company.user_agents.all()
                total_agents += len(user_agents)
                
                user_agents_data = []
                for user_agent in user_agents:
                    # Get document count for this agent
                    doc_count = AgentDocuments.query.filter_by(agent_id=user_agent.id).count()
                    
                    user_agents_data.append({
                        'id': user_agent.id,
                        'firstname': user_agent.firstname,
                        'lastname': user_agent.lastname,
                        'fullname': f"{user_agent.firstname} {user_agent.lastname}",
                        'idnumber': user_agent.idnumber,
                        'phone_number': user_agent.phone_number,
                        'is_authentic': user_agent.is_authentic,
                        'authenticity_desc': user_agent.authenticity_desc,
                        'date_of_birth': user_agent.date_of_birth.isoformat() if user_agent.date_of_birth else None,
                        'document_count': doc_count
                    })
                
                agent_companies_data.append({
                    'id': agent_company.id,
                    'company_name': agent_company.company_name,
                    'store_number': agent_company.store_number,
                    'location': agent_company.location,
                    'agent_count': len(user_agents_data),
                    'user_agents': user_agents_data
                })
            
            hierarchy.append({
                'id': company.id,
                'company_name': company.company_name,
                'registration_number': company.registration_number,
                'company_code': company.company_code,
                'shortcode': company.shortcode,
                'address': company.address,
                'compliance_status': company.compliance_status,
                'total_float_balance': float(company.total_float_balance),
                'registration_date': company.registration_date.isoformat() if company.registration_date else None,
                'agent_company_count': len(agent_companies_data),
                'total_agent_count': total_agents,
                'agent_companies': agent_companies_data
            })
        
        return jsonify({
            'success': True,
            'data': hierarchy,
            'total_companies': len(hierarchy)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@company_bp.route('/unassign-company/<int:agent_id>/<int:company_id>', methods=['POST'])
@jwt_required()
def unassign_agent_company(agent_id, company_id):
    """Unassign a specific company from an agent"""
    try:
        current_user_id = get_jwt_identity()
        
        # Verify agent exists
        agent = User.query.get_or_404(agent_id)
        if agent.role != 'agent':
            return jsonify({'error': 'User is not an agent'}), 400
        
        # Verify company exists and is assigned to this agent
        company = Company.query.filter_by(id=company_id, agent_user_id=agent_id).first()
        if not company:
            return jsonify({'error': 'Company not found or not assigned to this agent'}), 404
        
        # Unassign the company
        company.agent_user_id = None
        company.agent_assigned_at = None
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Company unassigned successfully',
            'agent_id': agent_id,
            'company_id': company_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@company_bp.route('/available-companies', methods=['GET'])
@jwt_required()
def get_available_companies_for_agent():
    """Get companies not assigned to any agent"""
    try:
        current_user_id = get_jwt_identity()

        # Get companies not assigned to any agent
        available_companies = Company.query.filter(Company.agent_user_id.is_(None)).all()
        
        companies_data = []
        for company in available_companies:
            company_data = {
                'id': company.id,
                'company_name': company.company_name,
                'registration_number': company.registration_number,
                'address': company.address,
                'primary_owner_name': company.primary_owner_name,
                'primary_owner_email': company.primary_owner_email,
                'primary_owner_shares': float(company.primary_owner_shares) if company.primary_owner_shares else 0.0,
                'compliance_status': company.compliance_status,
                'total_float_balance': float(company.total_float_balance) if company.total_float_balance else 0.0
            }
            
            # Add additional company details as needed
            companies_data.append(company_data)
        
        return jsonify({
            'success': True,
            'available_companies': companies_data,
            'total_available': len(companies_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@company_bp.route('/<int:agent_id>/agents', methods=['GET','OPTIONS'])
@jwt_required()
def get_agent_companies(agent_id):
    """Get all companies assigned to a specific agent"""
    try:
    
        # Verify agent exists and is actually an agent
        agent = User.query.get_or_404(agent_id)
        if agent.role != 'agent':
            return jsonify({'error': 'User is not an agent'}), 400
        
        # Get companies assigned to this agent
        companies = Company.query.filter_by(agent_user_id=agent_id).all()
        
        companies_data = []
        for company in companies:
            company_data = {
                'id': company.id,
                'company_name': company.company_name,
                'registration_number': company.registration_number,
                'address': company.address,
                'primary_owner_name': company.primary_owner_name,
                'primary_owner_email': company.primary_owner_email,
                'primary_owner_shares': float(company.primary_owner_shares) if company.primary_owner_shares else 0.0,
                'compliance_status': company.compliance_status,
                'total_float_balance': float(company.total_float_balance) if company.total_float_balance else 0.0,
                'registration_date': company.registration_date.isoformat() if company.registration_date else None,
                'company_code': company.company_code,
                'file_location': company.file_location,
                'assigned_at': company.agent_assigned_at.isoformat() if company.agent_assigned_at else None
            }
            
            # Add shareholders if available
            if hasattr(company, 'shareholders'):
                company_data['secondary_shareholders'] = [{
                    'name': sh.name,
                    'email': sh.email,
                    'shares': float(sh.shares) if sh.shares else 0.0
                } for sh in company.shareholders if sh.name != company.primary_owner_name]
            
            # Add directors if available
            if hasattr(company, 'directors'):
                company_data['directors'] = [{
                    'name': dir.name,
                    'email': dir.email
                } for dir in company.directors]
            
            companies_data.append(company_data)
        
        return jsonify({
            'success': True,
            'agent': {
                'id': agent.id,
                'username': agent.username,
                'email': agent.email,
                'phone_number': agent.phone_number
            },
            'companies': companies_data,
            'total_companies': len(companies_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@company_bp.route('/company-hierarchy/<int:company_id>', methods=['GET'])
@jwt_required()
def get_single_company_hierarchy(company_id):
    """
    Get hierarchical report for a single company
    """
    try:
        company = company_service.get_company_by_id(company_id=company_id)
        
        agent_companies = AgentCompany.query.filter_by(company_id=company.id).all()
        
        agent_companies_data = []
        total_agents = 0
        
        for agent_company in agent_companies:
            user_agents = agent_company.user_agents.all()
            total_agents += len(user_agents)
            
            user_agents_data = []
            for user_agent in user_agents:
                doc_count = AgentDocuments.query.filter_by(agent_id=user_agent.id).count()
                
                user_agents_data.append({
                    'id': user_agent.id,
                    'firstname': user_agent.firstname,
                    'lastname': user_agent.lastname,
                    'fullname': f"{user_agent.firstname} {user_agent.lastname}",
                    'idnumber': user_agent.idnumber,
                    'phone_number': user_agent.phone_number,
                    'is_authentic': user_agent.is_authentic,
                    'authenticity_desc': user_agent.authenticity_desc,
                    'date_of_birth': user_agent.date_of_birth.isoformat() if user_agent.date_of_birth else None,
                    'document_count': doc_count
                })
            
            agent_companies_data.append({
                'id': agent_company.id,
                'company_name': agent_company.company_name,
                'store_number': agent_company.store_number,
                'location': agent_company.location,
                'agent_count': len(user_agents_data),
                'user_agents': user_agents_data
            })
        
        data = {
            'id': company.id,
            'company_name': company.company_name,
            'registration_number': company.registration_number,
            'company_code': company.company_code,
            'shortcode': company.shortcode,
            'address': company.address,
            'compliance_status': company.compliance_status,
            'total_float_balance': float(company.total_float_balance),
            'registration_date': company.registration_date.isoformat() if company.registration_date else None,
            'agent_company_count': len(agent_companies_data),
            'total_agent_count': total_agents,
            'agent_companies': agent_companies_data
        }
        
        return jsonify({
            'success': True,
            'data': data
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@company_bp.route('/company/<int:id>', methods=['DELETE'])
def delete_company(id):
    success, error = company_service.delete_company(id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Company deleted successfully'}), 200

@company_bp.route('/company/validate-batch', methods=['POST'])
def validate_batch_company():
    file = request.files.get('file')
    result, error = company_service.validate_batch_company(file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(result), 200

@company_bp.route('/company/batch', methods=['POST'])
def batch_create_company():
    file = request.files.get('file')
    result, error = company_service.batch_create_company(file)
    if error:
        return jsonify({'error': error}), 400
    return jsonify(result), 201


# =============================================================================
# CR12 Document Management Endpoints
# =============================================================================

@company_bp.route('/<int:company_id>/cr12', methods=['GET'])
@jwt_required()
def get_cr12_document(company_id):
    """
    Get presigned download URL for CR12 document

    Returns:
        {
            "success": true,
            "download_url": "https://...",
            "filename": "cr12.pdf"
        }
    """
    try:
        company = company_service.get_company_by_id(company_id)
        if not company:
            return jsonify({'error': 'Company not found'}), 404

        if not company.file_location:
            return jsonify({'error': 'No CR12 document found for this company'}), 404

        # Get presigned URL (valid for 1 hour)
        download_url = company_service.get_file_url(company.file_location, expires=3600)
        if not download_url:
            return jsonify({'error': 'Failed to generate download URL'}), 500

        return jsonify({
            'success': True,
            'download_url': download_url,
            'object_name': company.file_location,
            'filename': f"CR12_{company.company_name.replace(' ', '_')}.pdf"
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@company_bp.route('/<int:company_id>/cr12', methods=['DELETE'])
@jwt_required()
def delete_cr12_document(company_id):
    """
    Delete CR12 document from storage

    Returns:
        {"success": true, "message": "CR12 document deleted successfully"}
    """
    try:
        current_user_id = get_jwt_identity()
        company = company_service.get_company_by_id(company_id)

        if not company:
            return jsonify({'error': 'Company not found'}), 404

        # Check ownership
        if company.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized: You can only manage your own company documents'}), 403

        if not company.file_location:
            return jsonify({'error': 'No CR12 document to delete'}), 404

        # Delete from MinIO
        deleted = company_service.delete_file(company.file_location)
        if not deleted:
            return jsonify({'error': 'Failed to delete file from storage'}), 500

        # Update company record
        company.file_location = None
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'CR12 document deleted successfully'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@company_bp.route('/<int:company_id>/cr12', methods=['POST'])
@jwt_required()
def upload_cr12_document(company_id):
    """
    Upload or re-upload CR12 document

    Request:
        - file: PDF file (multipart/form-data)

    Returns:
        {
            "success": true,
            "message": "CR12 document uploaded successfully",
            "file_location": "companies/cr12/abc123.pdf"
        }
    """
    try:
        current_user_id = get_jwt_identity()
        company = company_service.get_company_by_id(company_id)

        if not company:
            return jsonify({'error': 'Company not found'}), 404

        # Check ownership
        if company.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized: You can only manage your own company documents'}), 403

        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400

        if not company_service.allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Only PDF files are allowed'}), 400

        # Delete old file if exists
        if company.file_location:
            company_service.delete_file(company.file_location)

        # Upload new file
        file_location = company_service.save_file(file)
        if not file_location:
            return jsonify({'error': 'Failed to upload file'}), 500

        # Update company record
        company.file_location = file_location
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'CR12 document uploaded successfully',
            'file_location': file_location
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@company_bp.route('/<int:company_id>/cr12/download', methods=['GET'])
@jwt_required()
def download_cr12_document(company_id):
    """
    Direct download CR12 document (returns file bytes)
    """
    try:
        company = company_service.get_company_by_id(company_id)
        if not company:
            return jsonify({'error': 'Company not found'}), 404

        if not company.file_location:
            return jsonify({'error': 'No CR12 document found'}), 404

        # Get file bytes from MinIO
        file_bytes = company_service.get_file_bytes(company.file_location)
        if not file_bytes:
            return jsonify({'error': 'Failed to retrieve file'}), 500

        # Create response with file
        from flask import Response
        filename = f"CR12_{company.company_name.replace(' ', '_')}.pdf"

        response = Response(
            file_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': len(file_bytes)
            }
        )
        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500