# app/services/document_service.py
import os
import re
from werkzeug.utils import secure_filename
from google.cloud import storage
from flask import current_app
from app.model.agentcompany import  AgentCompany
from app.model.useragent import  UserAgent
from app.model.company import  Company
from app.model.agent_documents import AgentDocuments
from app.utils.kra_pin_details import extract_taxpayer_details
from app.utils.company_details import extract_company_number
from app.utils.police_clearance_details import extract_clearance_details

class DocumentProcessingService:
    def __init__(self, storage_client=None, bucket_name=None):
        self.storage_client = storage_client or current_app.storage_client
        self.bucket_name = bucket_name or current_app.config['GCP_BUCKET']

    def _get_company_id(self, agent_id):
        """Resolve company_id from agent via AgentCompany relationship"""

        if not agent_id:
            raise ValueError("Agent ID is required. Please provide a valid agent_id.")

        # Get a specific UserAgent by ID
        user_agent = UserAgent.query.filter_by(id=agent_id).first()

        if not user_agent:
            raise ValueError(f"Agent with ID {agent_id} not found. Please create the agent first.")

        # Then access their associated agent companies
        agent_companies = user_agent.agent_companies
        if len(agent_companies) > 0:
            company = agent_companies[0].company_id
            print(f"The company id is {company}")
            return company
        else:
            raise ValueError("Agent not associated with any company. Please link the agent to a company first.")

    def _upload_to_gcp(self, file_stream, company_id, agent_id, doc_type, filename):
        """Upload file to GCP with structured path"""
        blob_path = f"companies/{company_id}/agents/{agent_id}/{doc_type}/{filename}"
        bucket = self.storage_client.bucket(self.bucket_name)
        blob = bucket.blob(blob_path)
        file_stream.seek(0)  # Reset pointer
        blob.upload_from_file(file_stream, content_type=file_stream.content_type)
        print(f"The blob is {blob}")
        return blob.public_url, blob_path

    def _save_to_db(self, agent_id, company_id, doc_type, filename, gcp_url, gcp_path, extracted_data):
        """Persist document metadata"""
        doc = AgentDocuments(
            agent_id=agent_id,
            company_id=company_id,
            doc_type=doc_type,
            filename=filename,
            gcp_path=gcp_path,
            gcp_url=gcp_url,
            extracted_data=extracted_data
        )
        from app import db
        db.session.add(doc)
        db.session.commit()
        return doc
    
    def process_mpesa_agreement(self, file, agent_id):
        """
        Process Mpesa Agency Agreement document (no data extraction needed)
        """
        # 1. Resolve company
        company_id = self._get_company_id(agent_id)
        
        print(f"Processing Mpesa Agreement for Agent ID: {agent_id}, Company ID: {company_id}")

        # 2. Save temp
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', f"{agent_id}_mpesa_agreement_{filename}")
        
        print(f"Saving temporary file to: {temp_path}")
        file.save(temp_path)

        try:
            # 3. Upload to GCP (no extraction needed)
            file.seek(0)  # Reset for upload
            gcp_url, gcp_path = self._upload_to_gcp(file, company_id, agent_id, 'mpesa_agreement', filename)

            # 4. Save to DB with empty extracted_data
            doc = self._save_to_db(agent_id, company_id, 'mpesa_agreement', filename, gcp_url, gcp_path, {})

            # 5. Return
            return {
                "success": True,
                "gcp_url": gcp_url,
                "documentId": doc.id,
                "message": "Mpesa Agency Agreement uploaded successfully"
            }

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def process(self, file, agent_id, doc_type, extract_func):
        """
        Main processing pipeline:
        1. Resolve company
        2. Save temp file
        3. Extract data
        4. Upload to GCP
        5. Save to DB
        6. Cleanup
        """
        # 1. Resolve company
        company_id = self._get_company_id(agent_id)
        
        print(f"Processing document for Agent ID: {agent_id}, Company ID: {company_id}, Doc Type: {doc_type}")

        # 2. Save temp
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', f"{agent_id}_{doc_type}_{filename}")
        
        print(f"Saving temporary file to: {temp_path}")
        file.save(temp_path)

        try:
            # 3. Extract
            with open(temp_path, 'rb') as f:
                extracted = extract_func(temp_path)
                if extracted.get("error"):
                    raise ValueError(extracted["error"])

            gcp_url, gcp_path = None, None

            if self.storage_client:
                # 4. Upload
                file.seek(0)  # Reset for upload
                gcp_url, gcp_path = self._upload_to_gcp(file, company_id, agent_id, doc_type, filename)

                # 5. Save to DB
                self._save_to_db(agent_id, company_id, doc_type, filename, gcp_url, gcp_path, extracted)

            # 6. Return
            return {
                "success": True,
                "gcp_url": gcp_url,
                **extracted
            }

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)