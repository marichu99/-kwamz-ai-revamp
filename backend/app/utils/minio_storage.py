import logging
"""
MinIO Storage Utility
S3-compatible object storage for file uploads
"""

import os
import io
import uuid
from datetime import timedelta
from functools import lru_cache
from minio import Minio
from minio.error import S3Error
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class MinioStorage:
    """MinIO storage client for file operations"""

    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
        self.bucket = os.getenv('MINIO_BUCKET', 'kwamz-files')
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")

    def _generate_object_name(self, filename: str, folder: str = None) -> str:
        """Generate unique object name with optional folder prefix"""
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"

        if folder:
            return f"{folder}/{unique_name}"
        return unique_name

    def upload_file(self, file, folder: str = None, filename: str = None) -> dict:
        """
        Upload a file to MinIO

        Args:
            file: File object (from Flask request.files)
            folder: Optional folder/prefix for the object
            filename: Optional custom filename

        Returns:
            dict with object_name, url, and size
        """
        try:
            if filename is None:
                filename = secure_filename(file.filename)

            object_name = self._generate_object_name(filename, folder)

            # Read file content
            file_data = file.read()
            file_size = len(file_data)

            # Get content type
            content_type = file.content_type or 'application/octet-stream'

            # Upload to MinIO
            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(file_data),
                file_size,
                content_type=content_type
            )

            return {
                'success': True,
                'object_name': object_name,
                'bucket': self.bucket,
                'size': file_size,
                'content_type': content_type
            }

        except S3Error as e:
            return {
                'success': False,
                'error': str(e)
            }

    def upload_bytes(self, data: bytes, filename: str, folder: str = None,
                     content_type: str = 'application/octet-stream') -> dict:
        """
        Upload bytes directly to MinIO

        Args:
            data: Bytes to upload
            filename: Filename for the object
            folder: Optional folder/prefix
            content_type: MIME type

        Returns:
            dict with object_name and status
        """
        try:
            object_name = self._generate_object_name(filename, folder)

            self.client.put_object(
                self.bucket,
                object_name,
                io.BytesIO(data),
                len(data),
                content_type=content_type
            )

            return {
                'success': True,
                'object_name': object_name,
                'bucket': self.bucket,
                'size': len(data)
            }

        except S3Error as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_file(self, object_name: str) -> bytes:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(self.bucket, object_name)
            return response.read()
        except S3Error as e:
            logger.error(f"Error getting file: {e}")
            return None
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access

        Args:
            object_name: The object key
            expires: Expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string
        """
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

    def get_presigned_upload_url(self, object_name: str, expires: int = 3600) -> str:
        """
        Generate a presigned URL for direct upload

        Args:
            object_name: The object key
            expires: Expiration time in seconds

        Returns:
            Presigned PUT URL string
        """
        try:
            url = self.client.presigned_put_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned upload URL: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.client.remove_object(self.bucket, object_name)
            return True
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def list_files(self, prefix: str = None, recursive: bool = True) -> list:
        """List files in bucket with optional prefix filter"""
        try:
            objects = self.client.list_objects(
                self.bucket,
                prefix=prefix,
                recursive=recursive
            )
            return [
                {
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Error listing files: {e}")
            return []

    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists in the bucket"""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


# Singleton instance
@lru_cache(maxsize=1)
def get_minio_storage() -> MinioStorage:
    """Get or create MinIO storage instance"""
    return MinioStorage()


# Convenience function for quick uploads
def upload_to_minio(file, folder: str = None) -> dict:
    """Quick upload function"""
    storage = get_minio_storage()
    return storage.upload_file(file, folder)
