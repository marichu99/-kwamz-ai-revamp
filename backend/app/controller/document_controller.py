from flask import Blueprint, jsonify, request,current_app,send_file
from app.utils.kra_pin_details import extract_taxpayer_details
from app.utils.company_details import extract_company_number
from app.model.payment import Payment
from app.utils.police_clearance_details import extract_clearance_details
from app.utils.user_service import UserService
from app.model.agentcompany import  AgentCompany
from app.model.agent_documents import AgentDocuments
from app.utils.mpesa_automation import login_to_mpesa
from app.utils.script import authenticate_kra_from_app
from app import db
import os
import re
import io

document_bp = Blueprint('document', __name__)

@document_bp.route('/submit', methods=['POST'])
def submit():
    data = request.json
    kra_pin = data.get('kraPin')
    police_clearance = data.get('policeClearance')
    tax_payer_name = data.get('taxPayerName')
    id_number = data.get('idNumber')

    res = authenticate_kra_from_app(kra_pin=kra_pin, police_number=police_clearance, id_number=id_number,tax_payer_name=tax_payer_name)
    return jsonify({"success": res})
@document_bp.route('/extract_kra_pin', methods=['POST'])
def extract_kra_pin():
    """
    Upload/Re-upload KRA PIN document and extract details
    
    Request:
        - file: PDF file (multipart/form-data)
        - agent_id: ID of the agent
        
    Response:
        {
            "kraPin": "A123456789B",
            "taxPayerName": "John Doe",
            "email": "john@example.com",
            "gcp_url": "https://storage.googleapis.com/..."
        }
    """
    file = request.files.get('file')
    agent_id = request.form.get('agent_id') or None
    
    if not file:
        return jsonify({"error": "File and agent_id are required"}), 400

    try:
        # Check if document already exists (for re-upload)
        existing_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='kra_pin'
        ).first()
        
        # If re-uploading, delete old file from GCP
        if existing_doc:
            try:
                bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
                blob = bucket.blob(existing_doc.gcp_path)
                if blob.exists():
                    blob.delete()
            except Exception as e:
                print(f"Warning: Failed to delete old file: {str(e)}")
            
            # Delete old database record
            db.session.delete(existing_doc)
            db.session.commit()
        
        # Process the document
        result = current_app.document_service.process(
            file=file,
            agent_id=agent_id,
            doc_type='kra_pin',
            extract_func=extract_taxpayer_details
        )

        # Get the newly created document ID
        new_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='kra_pin'
        ).order_by(AgentDocuments.uploaded_at.desc()).first()

        return jsonify({
            "kraPin": result.get("PIN", ""),
            "taxPayerName": result.get("Taxpayer Name", ""),
            "email": result.get("Email Address", ""),
            "gcp_url": result.get("gcp_url", ""),
            "documentId": new_doc.id if new_doc else None
        }), 200

    except Exception as e:
        print(f"KRA PIN extraction error: {str(e)}")
        return jsonify({"error": str(e)}), 400


@document_bp.route('/extract_cr12', methods=['POST'])
def extract_cr12():
    """
    Upload/Re-upload CR12 document and extract company details

    Request:
        - file: PDF file (multipart/form-data)
        - agent_id: (Optional) ID of the agent - if provided, document is saved

    Response:
        {
            "cr12": "PVT-XXXXXX",
            "gcp_url": "https://storage.googleapis.com/..." (only if agent_id provided)
        }
    """
    import re
    import tempfile

    file = request.files.get('file')
    agent_id = request.form.get('agent_id') or None

    if not file:
        return jsonify({"error": "File is required"}), 400

    try:
        # If no agent_id, just extract data without saving (for company creation)
        if not agent_id:
            # Save to temp file for extraction
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name

            try:
                # Extract company number from document
                extracted = extract_company_number(temp_path)

                if extracted.get("error"):
                    return jsonify({"error": extracted["error"]}), 400

                # Validate CR12 extraction
                if re.search("Not Found", extracted.get("PIN", ""), re.IGNORECASE):
                    return jsonify({"error": "Kindly upload a valid CR12 document."}), 400

                return jsonify({
                    "cr12": extracted.get("PIN", ""),
                    "gcp_url": None
                }), 200
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # With agent_id - full processing with document storage
        # Check if document already exists (for re-upload)
        existing_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='cr12'
        ).first()

        # If re-uploading, delete old file from GCP
        if existing_doc:
            try:
                bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
                blob = bucket.blob(existing_doc.gcp_path)
                if blob.exists():
                    blob.delete()
            except Exception as e:
                print(f"Warning: Failed to delete old file: {str(e)}")

            # Delete old database record
            db.session.delete(existing_doc)
            db.session.commit()

        # Process the document (extract + save)
        result = current_app.document_service.process(
            file=file,
            agent_id=agent_id,
            doc_type='cr12',
            extract_func=extract_company_number
        )

        # Validate CR12 extraction
        if re.search("Not Found", result.get("PIN", ""), re.IGNORECASE):
            return jsonify({"error": "Kindly upload a valid CR12 document."}), 400

        return jsonify({
            "cr12": result.get("PIN", ""),
            "gcp_url": result.get("gcp_url", "")
        }), 200

    except Exception as e:
        print(f"CR12 extraction error: {str(e)}")
        return jsonify({"error": str(e)}), 400


@document_bp.route('/extract_police_clearance', methods=['POST'])
def extract_police_clearance():
    """
    Upload/Re-upload Police Clearance document and extract details
    
    Request:
        - file: PDF file (multipart/form-data)
        - agent_id: ID of the agent
        
    Response:
        {
            "refNo": "PC/2024/12345",
            "idNo": "12345678",
            "name": "John Doe",
            "gcp_url": "https://storage.googleapis.com/..."
        }
    """
    file = request.files.get('file')
    agent_id = request.form.get('agent_id') or None
    
    if not file:
        return jsonify({"error": "File and agent_id are required"}), 400
    
    try:
        # Check if document already exists (for re-upload)
        existing_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='police_clearance'
        ).first()
        
        # If re-uploading, delete old file from GCP
        if existing_doc:
            try:
                bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
                blob = bucket.blob(existing_doc.gcp_path)
                if blob.exists():
                    blob.delete()
            except Exception as e:
                print(f"Warning: Failed to delete old file: {str(e)}")
            
            # Delete old database record
            db.session.delete(existing_doc)
            db.session.commit()
        
        # Process the document
        result = current_app.document_service.process(
            file=file,
            agent_id=agent_id,
            doc_type='police_clearance',
            extract_func=extract_clearance_details
        )

        # Get the newly created document ID
        new_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='police_clearance'
        ).order_by(AgentDocuments.uploaded_at.desc()).first()

        return jsonify({
            "refNo": result.get("Reference Number", ""),
            "idNo": result.get("ID Number", ""),
            "name": result.get("Name", ""),
            "gcp_url": result.get("gcp_url", ""),
            "documentId": new_doc.id if new_doc else None
        }), 200

    except Exception as e:
        print(f"Police clearance extraction error: {str(e)}")
        return jsonify({"error": str(e)}), 400


@document_bp.route('/extract_mpesa_agreement', methods=['POST'])
def extract_mpesa_agreement():
    """
    Upload/Re-upload Mpesa Agency Agreement document
    
    Request:
        - file: PDF file (multipart/form-data)
        - agent_id: ID of the agent
        
    Response:
        {
            "gcp_url": "https://storage.googleapis.com/...",
            "documentId": 123,
            "message": "Mpesa Agency Agreement uploaded successfully"
        }
    """
    file = request.files.get('file')
    agent_id = request.form.get('agent_id') or None
    
    if not file :
        return jsonify({"error": "File and agent_id are required"}), 400
    
    try:
        # Check if document already exists (for re-upload)
        existing_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='mpesa_agreement'
        ).first()
        
        # If re-uploading, delete old file from GCP
        if existing_doc:
            try:
                bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
                blob = bucket.blob(existing_doc.gcp_path)
                if blob.exists():
                    blob.delete()
            except Exception as e:
                print(f"Warning: Failed to delete old file: {str(e)}")
            
            # Delete old database record
            db.session.delete(existing_doc)
            db.session.commit()
        
        # Process the document - Mpesa agreement doesn't need extraction
        result = current_app.document_service.process_mpesa_agreement(
            file=file,
            agent_id=agent_id
        )
        
        # Get the newly created document ID
        new_doc = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type='mpesa_agreement'
        ).order_by(AgentDocuments.uploaded_at.desc()).first()
        
        return jsonify({
            "gcp_url": result.get("gcp_url", ""),
            "documentId": new_doc.id if new_doc else None,
            "message": "Mpesa Agency Agreement uploaded successfully"
        }), 200
        
    except Exception as e:
        print(f"Mpesa Agreement upload error: {str(e)}")
        return jsonify({"error": str(e)}), 400

@document_bp.route('/delete/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    Delete a document from both GCP and database
    
    Path Parameter:
        - document_id: ID of the document to delete
        
    Response:
        {
            "success": true,
            "message": "Document deleted successfully"
        }
    """
    try:
        # Find the document
        document = AgentDocuments.query.get(document_id)
        
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        # Delete from GCP
        try:
            bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
            blob = bucket.blob(document.gcp_path)
            
            if blob.exists():
                blob.delete()
                print(f"Deleted file from GCP: {document.gcp_path}")
            else:
                print(f"Warning: File not found in GCP: {document.gcp_path}")
        except Exception as e:
            print(f"Warning: Failed to delete from GCP: {str(e)}")
            # Continue with database deletion even if GCP deletion fails
        
        # Delete from database
        doc_info = {
            "filename": document.filename,
            "doc_type": document.doc_type,
            "agent_id": document.agent_id
        }
        
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Document deleted successfully",
            "deleted_document": doc_info
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Delete error: {str(e)}")
        return jsonify({"error": "An error occurred during deletion"}), 500


@document_bp.route('/download/<int:document_id>', methods=['GET'])
def download_document(document_id):
    """
    Download a document from GCP
    
    Path Parameter:
        - document_id: ID of the document to download
        
    Query Parameters (optional):
        - inline: If 'true', display in browser; otherwise download as attachment
        
    Response:
        Returns the PDF file
    """
    try:
        # Find the document
        document = AgentDocuments.query.get(document_id)
        
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        # Download from GCP
        bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
        blob = bucket.blob(document.gcp_path)
        
        if not blob.exists():
            return jsonify({"error": "File not found in storage"}), 404
        
        # Download to memory
        file_content = blob.download_as_bytes()
        
        # Create a file-like object
        file_stream = io.BytesIO(file_content)
        
        # Determine if inline or attachment
        inline = request.args.get('inline', 'false').lower() == 'true'
        disposition = 'inline' if inline else 'attachment'
        
        return send_file(
            file_stream,
            mimetype='application/pdf',
            as_attachment=not inline,
            download_name=document.filename,
            max_age=0
        )
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({"error": "An error occurred during download"}), 500


@document_bp.route('/list/<int:agent_id>', methods=['GET'])
def list_agent_documents(agent_id):
    """
    List all documents for a specific agent
    
    Path Parameter:
        - agent_id: ID of the agent
        
    Query Parameters (optional):
        - doc_type: Filter by document type
        
    Response:
        {
            "success": true,
            "documents": [
                {
                    "id": 123,
                    "doc_type": "kra_pin",
                    "filename": "kra_document.pdf",
                    "uploaded_at": "2024-01-15T10:30:00",
                    "gcp_url": "https://...",
                    "extracted_data": {...}
                },
                ...
            ]
        }
    """
    try:
        query = AgentDocuments.query.filter_by(agent_id=agent_id)
        
        # Optional filtering by doc_type
        doc_type = request.args.get('doc_type')
        if doc_type:
            query = query.filter_by(doc_type=doc_type)
        
        documents = query.order_by(AgentDocuments.uploaded_at.desc()).all()
        
        documents_list = [
            {
                "id": doc.id,
                "doc_type": doc.doc_type,
                "filename": doc.filename,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "gcp_url": doc.gcp_url,
                "gcp_path": doc.gcp_path,
                "extracted_data": doc.extracted_data
            }
            for doc in documents
        ]
        
        return jsonify({
            "success": True,
            "count": len(documents_list),
            "documents": documents_list
        }), 200
        
    except Exception as e:
        print(f"List error: {str(e)}")
        return jsonify({"error": "An error occurred while fetching documents"}), 500


@document_bp.route('/status/<int:agent_id>/<doc_type>', methods=['GET'])
def get_document_status(agent_id, doc_type):
    """
    Check if a specific document type exists for an agent
    
    Path Parameters:
        - agent_id: ID of the agent
        - doc_type: Type of document to check
            
    Response:
        {
            "exists": true,
            "document": {
                "id": 123,
                "filename": "document.pdf",
                "uploaded_at": "2024-01-15T10:30:00"
            }
        }
    """
    try:
        document = AgentDocuments.query.filter_by(
            agent_id=agent_id,
            doc_type=doc_type
        ).first()
        
        if document:
            return jsonify({
                "exists": True,
                "document": {
                    "id": document.id,
                    "filename": document.filename,
                    "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
                    "gcp_url": document.gcp_url,
                    "extracted_data": document.extracted_data
                }
            }), 200
        else:
            return jsonify({
                "exists": False,
                "document": None
            }), 200
            
    except Exception as e:
        print(f"Status check error: {str(e)}")
        return jsonify({"error": "An error occurred while checking document status"}), 500


@document_bp.route('/download-all/<int:agent_id>', methods=['GET'])
def download_all_agent_documents(agent_id):
    """
    Download all documents for an agent as a ZIP file
    
    Path Parameter:
        - agent_id: ID of the agent
        
    Query Parameters (optional):
        - doc_types: Comma-separated list of doc_types to include (e.g., "kra_pin,police_clearance")
                    If not provided, all documents are included
        
    Response:
        Returns a ZIP file containing all agent documents
        Filename format: agent_{agent_id}_documents_{timestamp}.zip
    """
    import zipfile
    from datetime import datetime
    
    try:
        # Query documents for the agent
        query = AgentDocuments.query.filter_by(agent_id=agent_id)
        
        # Optional filtering by doc_types
        doc_types_param = request.args.get('doc_types')
        if doc_types_param:
            doc_types_list = [dt.strip() for dt in doc_types_param.split(',')]
            query = query.filter(AgentDocuments.doc_type.in_(doc_types_list))
        
        documents = query.all()
        
        if not documents:
            return jsonify({"error": "No documents found for this agent"}), 404
        
        # Create an in-memory ZIP file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            bucket = current_app.document_service.storage_client.bucket(current_app.document_service.bucket_name)
            
            for doc in documents:
                try:
                    # Download file from GCP
                    blob = bucket.blob(doc.gcp_path)
                    
                    if not blob.exists():
                        print(f"Warning: File not found in GCP: {doc.gcp_path}")
                        continue
                    
                    file_content = blob.download_as_bytes()
                    
                    # Create a structured path within the ZIP
                    # Format: doc_type/filename
                    zip_path = f"{doc.doc_type}/{doc.filename}"
                    
                    # Add file to ZIP
                    zip_file.writestr(zip_path, file_content)
                    
                except Exception as e:
                    print(f"Error adding file to ZIP: {doc.filename}, Error: {str(e)}")
                    continue
            
            # Add a manifest file with document metadata
            manifest_content = "Document Manifest\n"
            manifest_content += "=" * 50 + "\n\n"
            manifest_content += f"Agent ID: {agent_id}\n"
            manifest_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            manifest_content += f"Total Documents: {len(documents)}\n\n"
            
            for doc in documents:
                manifest_content += f"\nDocument Type: {doc.doc_type}\n"
                manifest_content += f"Filename: {doc.filename}\n"
                manifest_content += f"Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d %H:%M:%S') if doc.uploaded_at else 'N/A'}\n"
                manifest_content += "-" * 50 + "\n"
            
            zip_file.writestr("MANIFEST.txt", manifest_content)
        
        # Prepare ZIP for download
        zip_buffer.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"agent_{agent_id}_documents_{timestamp}.zip"
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename,
            max_age=0
        )
        
    except Exception as e:
        print(f"Download all error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An error occurred while creating the ZIP file"}), 500


@document_bp.route('/get-kyc', methods=['GET'])
def get_kyc():
    payments = Payment.query.all()
    return jsonify([{
        'id': payment.id,
        'reference_code': payment.reference_code,
        'phone_number': payment.phone_number,
        'user_name': getattr(UserService.get_user_by_id(user_id=payment.user_id), "username", "") if payment.user_id else "",
        'time_paid': payment.time_paid.isoformat() if payment.time_paid else ""
    } for payment in payments])

@document_bp.route('/test', methods=['GET'])
def test_imports():
    try:
        import playwright.sync_api
        from PIL import Image
        import pytesseract
        return jsonify({"message": "All imports work!"})
    except ImportError as e:
        return jsonify({"error": str(e)}), 500