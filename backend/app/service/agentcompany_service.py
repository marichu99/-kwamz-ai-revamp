from app import db
from app.model.agentcompany import AgentCompany
from app.model.company import Company
from datetime import datetime
import pandas as pd
import uuid
from flask import current_app

class AgentCompanyService:
    def __init__(self):
        self.upload_folder = 'Uploads'
        self.allowed_extensions = {'xlsx', 'xls'}

    def allowed_file(self, filename):
        """Check if the file extension is allowed."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def get_user_contact_info(self, contact_phone):
        """Format contact phone number."""
        if contact_phone and not contact_phone.startswith('0'):
            if contact_phone.startswith('+'):
                return contact_phone
            elif contact_phone.startswith('254'):
                return '0' + contact_phone[3:]
            else:
                return '0' + contact_phone
        return contact_phone

    def get_latest_company_code(self):
        """Generate a unique agent company code."""
        try:
            last_code = db.session.query(AgentCompany.agentcompany_code).order_by(
                AgentCompany.id.desc()
            ).first()

            if last_code and last_code[0]:
                last_num = int(last_code[0].split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1

            return f"agent-comp-{new_num:03d}", None
        except Exception as e:
            return None, f"Failed to generate company code: {str(e)}"

    def get_all_agent_companies_by_userid(self, user_id):
        """Retrieve all agent companies associated with a user ID."""
        try:
            agent_companies = AgentCompany.query.filter_by(user_id=user_id).all()
            return [{
                'id': ac.id,
                'company_name': ac.company_name,
                'registration_number': ac.registration_number,
                'location': ac.location,
                'contact_phone': self.get_user_contact_info(ac.contact_phone),
                'email': ac.email,
                'till_number': ac.till_number,
                'agentcompany_code': ac.agentcompany_code,
                'store_number': ac.store_number,
                'location_details': ac.location_details,
                'agent_number': ac.agent_number,
                'company_id': ac.company_id,
                'selected_company': ac.company_id,
                'established_date': ac.established_date.isoformat() if ac.established_date else None,
                'float_balance': ac.float_balance,
                'status': ac.status,
                'fraud_risk_level': ac.fraud_risk_level,
                'fraud_risk_description': ac.fraud_risk_description,
                'daily_transaction_limit': ac.daily_transaction_limit,
                'commission_rate': ac.commission_rate,
                'last_audit_date': ac.last_audit_date.isoformat() if ac.last_audit_date else None
            } for ac in agent_companies], None
        except Exception as e:
            current_app.logger.error(f"Error fetching agent companies for user {user_id}: {str(e)}")
            return [], f"Failed to fetch agent companies: {str(e)}"

    def create_agent_company(self, data, user_id):
        """Create a new agent company."""
        try:
            agent_company_code, error = self.get_latest_company_code()
            if error:
                return None, error

            company_id = data.get('selected_company')
            if company_id and not Company.query.get(company_id):
                return None, 'Invalid company_id'

            agent_company = AgentCompany(
                company_name=data.get('company_name'),
                registration_number=f"REG-{uuid.uuid4().hex[:8]}",
                location=data.get('location'),
                contact_phone=data.get('contact_phone'),
                email=data.get('email'),
                agentcompany_code=agent_company_code,
                till_number=data.get('till_number'),
                location_details=data.get('location_details'),
                store_number=data.get('store_number'),
                agent_number=data.get('agent_number'),
                company_id=company_id,
                established_date=datetime.strptime(data.get('established_date'), '%Y-%m-%d').date() if data.get('established_date') else None,
                float_balance=float(data.get('float_balance', 0.0)),
                status=data.get('status', 'active'),
                fraud_risk_level=data.get('fraud_risk_level', 'low'),
                fraud_risk_description=data.get('fraud_risk_description'),
                daily_transaction_limit=float(data.get('daily_transaction_limit', 0.0)),
                commission_rate=float(data.get('commission_rate', 0.0)),
                last_audit_date=datetime.strptime(data.get('last_audit_date'), '%Y-%m-%d').date() if data.get('last_audit_date') else None,
                user_id=user_id
            )
            db.session.add(agent_company)
            db.session.commit()
            return {
                'id': agent_company.id,
                'company_name': agent_company.company_name,
                'registration_number': agent_company.registration_number
            }, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating agent company: {str(e)}")
            return None, f"An error has occurred: {str(e)}"

    def update_agent_company(self, id, data, user_id):
        """Update an existing agent company."""
        try:
            agent_company = AgentCompany.query.get_or_404(id)
            if agent_company.user_id != user_id:
                return None, 'Unauthorized: You can only update your own agent companies'

            company_id = data.get('selected_company')
            if company_id and not Company.query.get(company_id):
                return None, 'Invalid company_id'

            agent_company.company_name = data.get('company_name', agent_company.company_name)
            agent_company.registration_number = data.get('registration_number', agent_company.registration_number)
            agent_company.location = data.get('location', agent_company.location)
            agent_company.contact_phone = data.get('contact_phone', agent_company.contact_phone)
            agent_company.email = data.get('email', agent_company.email)
            agent_company.agent_number = data.get('agent_number', agent_company.agent_number)
            agent_company.location_details = data.get('location_details', agent_company.location_details)
            agent_company.store_number = data.get('store_number', agent_company.store_number)
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
            agent_company.user_id = user_id

            db.session.commit()
            return {
                'id': agent_company.id,
                'company_name': agent_company.company_name,
                'status': agent_company.status
            }, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating agent company {id}: {str(e)}")
            return None, f"An error has occurred: {str(e)}"

    def delete_agent_company(self, id, user_id):
        """Delete an agent company."""
        try:
            agent_company = AgentCompany.query.get_or_404(id)
            if agent_company.user_id != user_id:
                return False, 'Unauthorized: You can only delete your own agent companies'
            db.session.delete(agent_company)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting agent company {id}: {str(e)}")
            return False, f"An error has occurred: {str(e)}"

    def validate_batch_agent_company(self, file):
        """Validate an Excel file for batch agent company creation."""
        try:
            if not self.allowed_file(file.filename):
                return None, None, 'Invalid file format. Only .xlsx allowed'

            df = pd.read_excel(file)
            required_columns = ['company_name', 'location_details', 'location(County)', 'agent_number', 'store_number', 'contact_details', 'status[active/inactive]']
            if not all(col in df.columns for col in required_columns):
                return None, None, 'Missing required columns'

            df['agent_number'] = df['agent_number'].astype(str)
            df['store_number'] = df['store_number'].astype(str)

            valid_agent_companies = []
            invalid_agent_companies = []

            for index, row in df.iterrows():
                errors = []
                if not row['company_name'] or pd.isna(row['company_name']):
                    errors.append('Company name is required')
                if not row['location(County)'] or pd.isna(row['location(County)']):
                    errors.append('Location (County) is required')
                if not row['location_details'] or pd.isna(row['location_details']):
                    errors.append('Location details is required')
                if not row['agent_number'] or pd.isna(row['agent_number']):
                    errors.append('Agent Number is required')
                if not row['store_number'] or pd.isna(row['store_number']):
                    errors.append('Store Number is required')
                if not row['contact_details'] or pd.isna(row['contact_details']):
                    errors.append('Phone Number for Contact is required')
                if not row['status[active/inactive]'] or pd.isna(row['status[active/inactive]']):
                    errors.append('Status on active/inactive is required')

                if pd.notna(row['agent_number']) and row['agent_number'].strip():
                    agent_number_str = str(row['agent_number']).strip()
                    if AgentCompany.query.filter_by(agent_number=agent_number_str).first():
                        errors.append(f'Agent number {agent_number_str} already exists')

                if pd.notna(row['store_number']) and row['store_number'].strip():
                    store_number_str = str(row['store_number']).strip()
                    if AgentCompany.query.filter_by(store_number=store_number_str).first():
                        errors.append(f'Store number {store_number_str} already exists')

                if errors:
                    invalid_agent_companies.append({'row': index + 2, 'data': row.to_dict(), 'errors': errors})
                else:
                    valid_agent_companies.append(row.to_dict())

            return valid_agent_companies, invalid_agent_companies, None
        except Exception as e:
            current_app.logger.error(f"Error validating batch agent companies: {str(e)}")
            return None, None, f"An error has occurred: {str(e)}"

    def batch_create_agent_company(self, file, user_id):
        """Create agent companies from an Excel file."""
        try:
            if not self.allowed_file(file.filename):
                return None, 0, 'Invalid file format. Only .xlsx allowed'

            df = pd.read_excel(file)
            created_agent_companies = []
            errors = []

            for index, row in df.iterrows():
                try:
                    company_name = str(row['company_name']).strip() if pd.notna(row.get('company_name')) else None
                    location_county = str(row['location(County)']).strip() if pd.notna(row.get('location(County)')) else None
                    location_details = str(row['location_details']).strip() if pd.notna(row.get('location_details')) else None
                    agent_number = str(row['agent_number']).strip() if pd.notna(row.get('agent_number')) else None
                    store_number = str(row['store_number']).strip() if pd.notna(row.get('store_number')) else None
                    contact_details = str(row['contact_details']).strip() if pd.notna(row.get('contact_details')) else None
                    status = str(row['status[active/inactive]']).strip() if pd.notna(row.get('status[active/inactive]')) else None

                    if not company_name:
                        errors.append(f"Row {index + 2}: Company name is required")
                        continue
                    if not location_county:
                        errors.append(f"Row {index + 2}: Location (County) is required")
                        continue
                    if not location_details:
                        errors.append(f"Row {index + 2}: Location details is required")
                        continue
                    if not agent_number:
                        errors.append(f"Row {index + 2}: Agent number is required")
                        continue
                    if not store_number:
                        errors.append(f"Row {index + 2}: Store number is required")
                        continue

                    existing_company = AgentCompany.query.filter_by(agent_number=agent_number).first()
                    if existing_company:
                        errors.append(f"Row {index + 2}: Agent number {agent_number} already exists")
                        continue

                    existing_company_store = AgentCompany.query.filter_by(store_number=store_number).first()
                    if existing_company_store:
                        errors.append(f"Row {index + 2}: Store number {store_number} already exists")
                        continue

                    registration_number = f"REG-{uuid.uuid4().hex[:8].upper()}"
                    agent_company_code, error = self.get_latest_company_code()
                    if error:
                        errors.append(f"Row {index + 2}: {error}")
                        continue

                    agent_company = AgentCompany(
                        company_name=company_name,
                        registration_number=registration_number,
                        location=location_county,
                        location_details=location_details,
                        contact_phone=str(contact_details),
                        email=str(row.get('email')).strip() if pd.notna(row.get('email')) else None,
                        agentcompany_code=agent_company_code,
                        agent_number=agent_number,
                        store_number=str(row.get('store_number')).strip() if pd.notna(row.get('store_number')) else None,
                        till_number=str(row.get('till_number')).strip() if pd.notna(row.get('till_number')) else None,
                        established_date=datetime.strptime(row['established_date'], '%Y-%m-%d').date() if pd.notna(row.get('established_date')) and row.get('established_date') else None,
                        float_balance=float(row.get('float_balance', 0.0)),
                        status=status if status in ['active', 'inactive'] else 'inactive',
                        fraud_risk_level=row.get('fraud_risk_level', 'low'),
                        fraud_risk_description=str(row.get('fraud_risk_description')).strip() if pd.notna(row.get('fraud_risk_description')) else None,
                        daily_transaction_limit=float(row.get('daily_transaction_limit', 0.0)),
                        commission_rate=float(row.get('commission_rate', 0.0)),
                        last_audit_date=datetime.strptime(row['last_audit_date'], '%Y-%m-%d').date() if pd.notna(row.get('last_audit_date')) and row.get('last_audit_date') else None,
                        company_id=int(row['company_id']) if pd.notna(row.get('company_id')) and row.get('company_id') else None,
                        user_id=user_id
                    )

                    db.session.add(agent_company)
                    created_agent_companies.append({
                        'id': agent_company.id,
                        'company_name': agent_company.company_name,
                        'agent_number': agent_company.agent_number,
                        'store_number': agent_company.store_number
                    })

                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    continue

            if errors:
                db.session.rollback()
                return None, len(errors), errors

            db.session.commit()
            return created_agent_companies, 0, None

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in batch create agent companies: {str(e)}")
            return None, 1, f"Batch upload failed: {str(e)}"