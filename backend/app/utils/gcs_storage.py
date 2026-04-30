"""
Google Cloud Storage Utility
For storing user agent profile images
"""

import os
import uuid
from google.cloud import storage
from google.api_core.exceptions import GoogleAPIError


ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_IMAGE_MIMETYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}


def _is_allowed_image(file) -> bool:
    """Validate by both extension and MIME type."""
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    mime = (file.content_type or '').lower().split(';')[0].strip()
    return ext in ALLOWED_IMAGE_EXTENSIONS and mime in ALLOWED_IMAGE_MIMETYPES


def _get_client_and_bucket():
    bucket_name = os.getenv('GCP_BUCKET', 'trovana-docs')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path and not os.path.isabs(credentials_path):
        # Resolve relative path from backend root
        credentials_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            credentials_path
        )
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    return client, bucket


def upload_agent_image(file, user_agent_id: int) -> dict:
    """
    Upload a user agent profile image to GCS.

    Args:
        file: Werkzeug FileStorage object from request.files
        user_agent_id: ID of the user agent (used in the object path)

    Returns:
        dict with 'success', 'gcs_path', and optionally 'error'
    """
    if not file or not file.filename:
        return {'success': False, 'error': 'No file provided'}

    if not _is_allowed_image(file):
        return {
            'success': False,
            'error': f'Invalid file type. Allowed image types: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}'
        }

    try:
        ext = file.filename.rsplit('.', 1)[-1].lower()
        object_name = f"useragents/profiles/{user_agent_id}/{uuid.uuid4().hex}.{ext}"
        content_type = file.content_type or f'image/{ext}'

        _, bucket = _get_client_and_bucket()
        blob = bucket.blob(object_name)
        file.seek(0)
        blob.upload_from_file(file, content_type=content_type)

        return {'success': True, 'gcs_path': object_name}

    except GoogleAPIError as e:
        return {'success': False, 'error': f'GCS upload failed: {str(e)}'}
    except Exception as e:
        return {'success': False, 'error': f'Upload error: {str(e)}'}


def delete_agent_image(gcs_path: str) -> bool:
    """Delete an image from GCS. Returns True on success."""
    if not gcs_path:
        return True
    try:
        _, bucket = _get_client_and_bucket()
        blob = bucket.blob(gcs_path)
        if blob.exists():
            blob.delete()
        return True
    except (GoogleAPIError, Exception):
        return False


def get_agent_image_url(gcs_path: str, expires_seconds: int = 3600) -> str:
    """
    Generate a signed URL for temporary access to an agent image.

    Returns signed URL string, or None on failure.
    """
    if not gcs_path:
        return None
    try:
        from datetime import timedelta
        _, bucket = _get_client_and_bucket()
        blob = bucket.blob(gcs_path)
        url = blob.generate_signed_url(expiration=timedelta(seconds=expires_seconds), method='GET')
        return url
    except Exception:
        return None
