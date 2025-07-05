import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError
import logging

logger = logging.getLogger(__name__)


class AudioBlobStorageClient:
    """Azure Blob Storage client for audio files"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
        self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
        self.container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'audio')
        
        if not self.account_name or not self.account_key:
            raise ValueError("Azure Storage account name and key must be set in environment variables")
        
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Ensure container exists
        self._ensure_container_exists()
    
    def _ensure_container_exists(self):
        """Ensure the audio container exists"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
        except AzureError as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise
    
    def upload_audio_file(
        self, 
        audio_data: bytes, 
        session_id: Optional[str] = None,
        audio_format: str = "webm"
    ) -> tuple[str, str]:
        """
        Upload audio file to Blob Storage
        
        Args:
            audio_data: Audio file binary data
            session_id: Session ID for organizing files
            audio_format: File format extension
            
        Returns:
            Tuple of (audio_id, blob_url)
        """
        try:
            audio_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            # Organize files by session if provided
            if session_id:
                blob_name = f"audio/{session_id}/{audio_id}_{timestamp}.{audio_format}"
            else:
                blob_name = f"audio/{audio_id}_{timestamp}.{audio_format}"
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload file with metadata
            blob_client.upload_blob(
                audio_data,
                overwrite=True,
                metadata={
                    'audio_id': audio_id,
                    'session_id': session_id or 'no-session',
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'format': audio_format
                }
            )
            
            blob_url = blob_client.url
            logger.info(f"Uploaded audio file: {blob_name}")
            
            return audio_id, blob_url
            
        except AzureError as e:
            logger.error(f"Error uploading audio file: {e}")
            raise
    
    def generate_sas_url(self, blob_url: str, expire_hours: int = 1) -> tuple[str, datetime]:
        """
        Generate SAS URL for blob access
        
        Args:
            blob_url: Full blob URL
            expire_hours: SAS token expiration in hours
            
        Returns:
            Tuple of (sas_url, expiry_datetime)
        """
        try:
            # Extract blob name from URL
            blob_name = blob_url.split(f'{self.container_name}/')[-1]
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expire_hours)
            )
            
            sas_url = f"{blob_url}?{sas_token}"
            expiry = datetime.utcnow() + timedelta(hours=expire_hours)
            
            return sas_url, expiry
            
        except AzureError as e:
            logger.error(f"Error generating SAS URL: {e}")
            raise
    
    def delete_audio_file(self, blob_url: str) -> bool:
        """
        Delete audio file from Blob Storage
        
        Args:
            blob_url: Full blob URL
            
        Returns:
            True if deleted successfully
        """
        try:
            blob_name = blob_url.split(f'{self.container_name}/')[-1]
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Deleted audio file: {blob_name}")
            return True
            
        except AzureError as e:
            logger.error(f"Error deleting audio file: {e}")
            return False
