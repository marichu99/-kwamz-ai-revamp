import logging
from typing import List
from app.model.company import Company
from app.model.shareholder import Shareholder
from app.model.director import Director
from datetime import datetime
import threading
from app.utils.email_utils import send_welcome_pack_email
from decimal import Decimal, InvalidOperation
from app import db
import json
from sqlalchemy import and_
import uuid
import os
import pandas as pd
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import current_app
from datetime import timedelta

logger = logging.getLogger(__name__)

class CompanyService:
    def __init__(self, db):
        self.db = db
        self.UPLOAD_FOLDER = 'uploads'
        self.ALLOWED_EXTENSIONS = {'pdf', 'xlsx'}
        if not os.path.exists(self.UPLOAD_FOLDER):
            os.makedirs(self.UPLOAD_FOLDER)

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def _get_gcp_client(self):
        """Get GCP storage client from app context"""
        if hasattr(current_app, 'document_service') and current_app.document_service:
            return current_app.document_service.storage_client, current_app.document_service.bucket_name
        return None, None

    def save_file(self, file, company_id=None):
        """Save file to GCP Cloud Storage"""
        if file and self.allowed_file(file.filename):
            try:
                storage_client, bucket_name = self._get_gcp_client()
                if not storage_client:
                    logger.info("GCP storage client not available")
                    return None

                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"

                # Build path: companies/cr12/{company_id or 'new'}/{unique_name}
                folder = f"companies/cr12/{company_id or 'pending'}"
                blob_path = f"{folder}/{unique_name}"

                # Upload to GCP
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                file.seek(0)
                blob.upload_from_file(file, content_type=file.content_type or 'application/pdf')

                logger.info(f"File uploaded to GCP: {blob_path}")
                return blob_path

            except Exception as e:
                logger.error(f"Error uploading to GCP: {e}")
                return None
        return None

    def delete_file(self, gcp_path: str) -> bool:
        """Delete file from GCP Cloud Storage"""
        if not gcp_path:
            return False
        try:
            storage_client, bucket_name = self._get_gcp_client()
            if not storage_client:
                logger.info("GCP storage client not available")
                return False

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(gcp_path)

            if blob.exists():
                blob.delete()
                logger.info(f"File deleted from GCP: {gcp_path}")
                return True
            else:
                logger.warning(f"File not found in GCP: {gcp_path}")
                return True  # Consider it deleted if not found

        except Exception as e:
            logger.error(f"Error deleting from GCP: {e}")
            return False

    def get_file_url(self, gcp_path: str, expires: int = 3600) -> str:
        """Get signed URL for file download from GCP"""
        if not gcp_path:
            return None
        try:
            storage_client, bucket_name = self._get_gcp_client()
            if not storage_client:
                logger.info("GCP storage client not available")
                return None

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(gcp_path)

            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires),
                method="GET"
            )
            return url

        except Exception as e:
            logger.error(f"Error getting signed URL from GCP: {e}")
            return None

    def get_file_bytes(self, gcp_path: str) -> bytes:
        """Get file bytes from GCP Cloud Storage"""
        if not gcp_path:
            return None
        try:
            storage_client, bucket_name = self._get_gcp_client()
            if not storage_client:
                logger.info("GCP storage client not available")
                return None

            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(gcp_path)

            return blob.download_as_bytes()

        except Exception as e:
            logger.error(f"Error getting file from GCP: {e}")
            return None

    def get_companies(self):
        """Retrieve all companies."""
        try:
            companies = Company.query.all()
            return [{
                'id': c.id,
                'company_name': c.company_name,
                'company_number': c.registration_number,  # Changed to match frontend
                'registration_number': c.registration_number,  # Keep both for compatibility
                'registration_date': c.registration_date.isoformat() if c.registration_date else None,
                'address': c.address,
                'primary_owner_name': c.primary_owner_name,
                'primary_owner_email': c.primary_owner_email,
                'primary_owner_shares': float(c.primary_owner_shares) if c.primary_owner_shares else 0.0,
                'secondary_shareholders': [{
                    'name': sh.name,
                    'email': sh.email,
                    'shares': float(sh.shares) if sh.shares else 0.0
                } for sh in c.shareholders if sh.name != c.primary_owner_name],  
                'directors': [{
                    'name': dir.name,
                    'email': dir.email,
                } for dir in c.directors],
                'cr12_file_location': c.file_location,
                'compliance_status': c.compliance_status,
                'total_float_balance': float(c.total_float_balance) if c.total_float_balance else 0.0,
                # Add user information if company is linked to a user
                'user_id': c.user_id,
                'agent_user_id': c.agent_user_id
            } for c in companies], None
        except Exception as e:
            logger.error(f"Error retrieving companies: {str(e)}")
            return None, str(e)
    
    def get_companies_by_user_id(self, user_id:int) ->List[Company]:
        try:
            return Company.query.filter_by(user_id=user_id).all()
        except Exception as e:
            logger.error(f"The error on fetching companies is {str(e)}")
            return []
    def get_companies_by_userid(self,user_id):
        """Retrieve all companies."""
        try:
            companies = Company.query.filter_by(user_id=user_id).all()
            return [{
                'id': c.id,
                'company_name': c.company_name,
                'company_number': c.registration_number,  # Changed to match frontend
                'registration_date': c.registration_date.isoformat() if c.registration_date else None,  # Format date
                'address': c.address,
                'shortcode': c.shortcode,
                'primary_owner_name': c.primary_owner_name,
                'primary_owner_email': c.primary_owner_email,  # Added this field
                'primary_owner_shares': float(c.primary_owner_shares) if c.primary_owner_shares else 0.0,
                'secondary_shareholders': [{
                    'name': sh.name,
                    'email': sh.email,
                    'shares': float(sh.shares) if sh.shares else 0.0
                } for sh in c.shareholders if sh.name != c.primary_owner_name],  
                'directors': [{
                    'name': dir.name,
                    'email': dir.email
                } for dir in c.directors],  # Assuming directors relationship
                'cr12_file_location': c.file_location,  # For preview
                'compliance_status': c.compliance_status,
                'agent_user_id': c.agent_user_id,
                'total_float_balance': float(c.total_float_balance) if c.total_float_balance else 0.0
            } for c in companies], None
        except Exception as e:
            logger.error(f"Error retrieving companies: {str(e)}")
            return None, str(e)
        
    def get_company_by_id(self, company_id):
        """Retrieve a company by ID."""
        return self.db.session.query(Company).filter_by(id=company_id).first()

    def get_company_by_shortcode(self, company_shortcode):
        """Retrieve a company by shortcode."""
        return self.db.session.query(Company).filter_by(shortcode=company_shortcode).first()

    def create_company(self, company_data):
        """Create a new company."""
        company = Company(**company_data)
        self.db.session.add(company)
        self.db.session.commit()
        return company
    
    def update_company(self, company_id, update_data, file=None):
        """Update an existing company with relationships."""
        company = self.get_company_by_id(company_id)
        if not company:
            return None, "Company not found"

        company.user_id = update_data["user_id"]
        logger.info(f"The shortcode is {update_data['shortcode']}")

        try:
            # Handle file upload - delete old file if re-uploading
            file_location = company.file_location
            if file and self.allowed_file(file.filename):
                # Delete old file from MinIO if it exists
                if company.file_location:
                    self.delete_file(company.file_location)
                # Upload new file
                file_location = self.save_file(file)

            # Update basic company fields
            basic_fields = [
                'company_name', 'registration_number', 'registration_date', 
                'address', 'primary_owner_name', 'primary_owner_email',
                'primary_owner_shares','shortcode', 'total_float_balance', 'compliance_status'
            ]
            
            for field in basic_fields:
                if field in update_data:
                    value = update_data[field]
                    if field in ['primary_owner_shares', 'total_float_balance'] and value is not None:
                        value = Decimal(str(value))
                    setattr(company, field, value)

            # Update file location if new file was uploaded
            if file_location:
                company.file_location = file_location

            # Handle shareholders relationships
            if 'secondary_shareholders' in update_data:
                shareholders_data = update_data['secondary_shareholders']
                existing_shareholders = {sh.email: sh for sh in company.shareholders if sh.email}
                
                # Process each shareholder from the update data
                for sh_data in shareholders_data:
                    email = sh_data.get('email', '').strip().lower()
                    name = sh_data.get('name', '')
                    shares = Decimal(str(sh_data.get('shares', 0)))
                    
                    if email:  # Only process if email exists
                        if email in existing_shareholders:
                            # Update existing shareholder
                            shareholder = existing_shareholders[email]
                            shareholder.name = name
                            shareholder.shares = shares
                        else:
                            # Create new shareholder
                            shareholder = Shareholder(
                                name=name,
                                email=email,
                                shares=shares,
                                company_id=company.id
                            )
                            self.db.session.add(shareholder)
                
                # Remove shareholders that are no longer in the update data
                updated_emails = {sh.get('email', '').strip().lower() for sh in shareholders_data if sh.get('email')}
                for existing_email, shareholder in existing_shareholders.items():
                    if existing_email not in updated_emails:
                        self.db.session.delete(shareholder)

            # Handle directors relationships
            if 'directors' in update_data:
                directors_data = update_data['directors']
                existing_directors = {dir.email: dir for dir in company.directors if dir.email}
                
                # Process each director from the update data
                for dir_data in directors_data:
                    email = dir_data.get('email', '').strip().lower()
                    name = dir_data.get('name', '')
                    
                    if email:  # Only process if email exists
                        if email in existing_directors:
                            # Update existing director
                            director = existing_directors[email]
                            director.name = name
                        else:
                            # Create new director
                            director = Director(
                                name=name,
                                email=email,
                                company_id=company.id
                            )
                            self.db.session.add(director)
                
                # Remove directors that are no longer in the update data
                updated_emails = {dir.get('email', '').strip().lower() for dir in directors_data if dir.get('email')}
                for existing_email, director in existing_directors.items():
                    if existing_email not in updated_emails:
                        self.db.session.delete(director)

            self.db.session.commit()
            
            # Return complete company data including relationships
            return {
                'id': company.id,
                'company_name': company.company_name,
                'registration_number': company.registration_number,
                'registration_date': company.registration_date.isoformat() if company.registration_date else None,
                'address': company.address,
                'primary_owner_name': company.primary_owner_name,
                'primary_owner_email': company.primary_owner_email,
                'primary_owner_shares': float(company.primary_owner_shares) if company.primary_owner_shares else 0.0,
                'file_location': company.file_location,
                'compliance_status': company.compliance_status,
                'total_float_balance': float(company.total_float_balance) if company.total_float_balance else 0.0,
                'secondary_shareholders': [{
                    'name': sh.name,
                    'email': sh.email,
                    'shares': float(sh.shares) if sh.shares else 0.0
                } for sh in company.shareholders],
                'directors': [{
                    'name': dir.name,
                    'email': dir.email
                } for dir in company.directors]
            }, None
            
        except Exception as e:
            self.db.session.rollback()
            return None, str(e)
        
    def delete_company(self, company_id):
        """Delete a company by ID."""
        company = self.get_company_by_id(company_id)
        if not company:
            return False, "Company not found"
        try:
            self.db.session.delete(company)
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)
    def onboard_company(self, company_data):
        """
        Onboard a company with shareholders and directors, and send welcome emails in a separate thread.
        """
        try:
            # Debug: Print received data structure
            logger.info(f"Raw company_data type: {type(company_data)}")
            logger.info(f"Raw company_data: {company_data}")
            
            # Input validation
            required_fields = ['company_name', 'address', 'shortcode']
            if not all(field in company_data and company_data[field] for field in required_fields):
                raise ValueError("Company name, address, and shortcode are required.")
            # company_number (registration number) is optional — omit the check
            if not isinstance(company_data.get('shortcode'), str) or not company_data['shortcode'].strip():
                raise ValueError("Shortcode must be a non-empty string.")
            if not 5 <= len(company_data['shortcode']) <= 10 or not company_data['shortcode'].isdigit():
                raise ValueError("Shortcode must be a 5-10 digit number.")

            # Generate unique company code if not provided
            company_code = company_data.get('company_number') or str(uuid.uuid4())[:8].upper()
            file_location = company_data.get('file_location') or None

            # Handle file if provided
            if 'cr12_file' in company_data and company_data['cr12_file']:
                file_location = self.save_file(company_data['cr12_file'])

            # Safely calculate total shares with type conversion
            primary_shares = Decimal('0.00')
            try:
                primary_shares = Decimal(str(company_data.get('primary_owner_shares', '0.00')))
            except (TypeError, ValueError, InvalidOperation):
                primary_shares = Decimal('0.00')

            # Handle secondary_shareholders - could be stringified JSON
            secondary_shareholders = company_data.get('secondary_shareholders', [])
            secondary_shares = Decimal('0.00')
            
            logger.info(f"Secondary shareholders raw: {secondary_shareholders}")
            logger.info(f"Secondary shareholders type: {type(secondary_shareholders)}")
            
            # Parse if it's a JSON string
            if isinstance(secondary_shareholders, str):
                try:
                    secondary_shareholders = json.loads(secondary_shareholders)
                    logger.info(f"Parsed secondary_shareholders: {secondary_shareholders}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse secondary_shareholders JSON: {e}")
                    secondary_shareholders = []
            
            # Ensure it's a list and handle each item safely
            if isinstance(secondary_shareholders, list):
                for sh in secondary_shareholders:
                    if isinstance(sh, dict):  # Ensure it's a dictionary
                        try:
                            shares_value = sh.get('shares', '0.00')
                            secondary_shares += Decimal(str(shares_value))
                        except (TypeError, ValueError, InvalidOperation):
                            # Skip invalid share values
                            continue
                    else:
                        logger.warning(f"Warning: shareholder item is not a dict: {type(sh)} - {sh}")
            else:
                # If it's not a list, log and treat as empty
                logger.warning(f"Warning: secondary_shareholders is not a list: {type(secondary_shareholders)}")
                secondary_shareholders = []

            logger.info(f"Primary shares: {primary_shares}, Secondary shares: {secondary_shares}")
            
            total_shares = primary_shares + secondary_shares
            if abs(total_shares - Decimal('100.00')) > Decimal('0.01'):
                raise ValueError(f"Total shareholding must equal 100%, got {total_shares:.2f}%")

            # Handle directors - could be stringified JSON
            directors = company_data.get('directors', [])
            if isinstance(directors, str):
                try:
                    directors = json.loads(directors)
                    logger.info(f"Parsed directors: {directors}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse directors JSON: {e}")
                    directors = []
            
            if not isinstance(directors, list):
                directors = []

            # Start transaction
            with self.db.session.begin():
                # Handle registration date parsing
                registration_date = None
                if company_data.get('registration_date'):
                    try:
                        registration_date = datetime.strptime(company_data['registration_date'], '%Y-%m-%d').date()
                    except ValueError as e:
                        logger.warning(f"Invalid registration date format: {e}")
                        # Continue without registration date

                company = Company(
                    id=company_data.get('id') or None,
                    company_name=company_data['company_name'],
                    registration_number=company_data.get('company_number') or None,
                    registration_date=registration_date,
                    primary_owner_name=company_data['primary_owner_name'],
                    primary_owner_email=company_data['primary_owner_email'],
                    primary_owner_shares=company_data['primary_owner_shares'],
                    address=company_data['address'],
                    company_code=company_code,
                    file_location=file_location,
                    user_id=company_data["user_id"],
                    shortcode=company_data["shortcode"],
                )

                # Add primary shareholder
                if company_data.get('primary_owner_name') and primary_shares > 0:
                    primary_shareholder = Shareholder(
                        company_id=company.id,
                        name=company_data['primary_owner_name'],
                        email=company_data.get('primary_owner_email'),
                        shares=primary_shares
                    )
                    company.shareholders.append(primary_shareholder)

                # Add secondary shareholders safely
                for sh in secondary_shareholders:
                    if isinstance(sh, dict) and sh.get('name'):
                        try:
                            shares_value = Decimal(str(sh.get('shares', '0.00')))
                            if shares_value > 0:
                                shareholder = Shareholder(
                                    company_id=company.id,
                                    name=sh['name'],
                                    email=sh.get('email'),
                                    shares=shares_value
                                )
                                company.shareholders.append(shareholder)
                        except (TypeError, ValueError, InvalidOperation):
                            # Skip shareholders with invalid share values
                            logger.warning(f"Invalid shares value for shareholder: {sh}")
                            continue

                # Add directors safely
                for dir_data in directors:
                    if isinstance(dir_data, dict) and dir_data.get('name'):
                        director = Director(
                            company_id=company.id,
                            name=dir_data['name'],
                            email=dir_data.get('email')
                        )
                        company.directors.append(director)

                # Validate at least one shareholder
                if not company.shareholders:
                    raise ValueError("At least one shareholder is required.")

                self.db.session.add(company)
                self.db.session.flush()  # Assigns company.id
   
                # Send to primary owner (if they have an email and shares)
                if company_data.get('primary_owner_email') and primary_shares > 0:
                    send_welcome_pack_email(
                        recipient_email=company_data['primary_owner_email'],
                        recipient_name=company_data['primary_owner_name'],
                        role='shareholder',
                        company_data=company_data,
                        cr12_file_path=file_location
                    )

                # Send to secondary shareholders
                for sh in secondary_shareholders:
                    if isinstance(sh, dict) and sh.get('email') and sh.get('shares', 0) > 0:
                        send_welcome_pack_email(
                            recipient_email=sh['email'],
                            recipient_name=sh['name'],
                            role='shareholder',
                            company_data=company_data,
                            cr12_file_path=file_location
                        )

                # Send to directors
                for dir_data in directors:
                    if isinstance(dir_data, dict) and dir_data.get('email'):
                        send_welcome_pack_email(
                            recipient_email=dir_data['email'],
                            recipient_name=dir_data['name'],
                            role='director',
                            company_data=company_data,
                            cr12_file_path=file_location
                        )

            return company.id, "Company onboarded successfully"
        except ValueError as ve:
            self.db.session.rollback()
            logger.error(f"Validation error: {str(ve)}")
            return None, str(ve)
        except IntegrityError as ie:
            self.db.session.rollback()
            logger.error(f"Integrity error: {str(ie)}")        
            return None, "It is most likely that the company has already been onboarded"
        except SQLAlchemyError as sae:
            self.db.session.rollback()
            logger.error(f"SQLAlchemy error: {str(sae)}")
            return None, str(sae)
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Unexpected error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, f"Failed to onboard company: {str(e)}"
    def validate_batch_company(self, file):
        """Validate a batch of companies from an Excel file."""
        try:
            if not file or not self.allowed_file(file.filename):
                return None, "Invalid file format. Only .xlsx allowed"

            df = pd.read_excel(file)
            required_columns = ['company_name', 'registration_number', 'address', 'primary_owner_name', 'primary_owner_id']
            if not all(col in df.columns for col in required_columns):
                return None, "Missing required columns"

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

            return {'validCompanies': valid_companies, 'invalidCompanies': invalid_companies}, None
        except Exception as e:
            return None, str(e)

    def batch_create_company(self, file):
        """Create multiple companies from a validated Excel file."""
        try:
            if not file or not self.allowed_file(file.filename):
                return None, "Invalid file format. Only .xlsx allowed"

            df = pd.read_excel(file)
            created_companies = []
            with self.db.session.begin():
                for _, row in df.iterrows():
                    company = Company(
                        company_name=row['company_name'],
                        registration_number=row['registration_number'],
                        address=row['address'],
                        primary_owner_name=row['primary_owner_name'],
                        primary_owner_id=row['primary_owner_id'],
                        compliance_status=row.get('compliance_status', 'under_review'),
                        total_float_balance=Decimal(str(row.get('total_float_balance', 0.0)))
                    )
                    self.db.session.add(company)
                    self.db.session.flush()  # Assigns company.id
                    created_companies.append({'id': company.id, 'company_name': company.company_name})

            return {
                'message': f'{len(created_companies)} companies created successfully',
                'createdCompanies': created_companies
            }, None
        except Exception as e:
            self.db.session.rollback()
            return None, str(e)