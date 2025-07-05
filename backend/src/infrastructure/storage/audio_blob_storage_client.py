import os
import uuid
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError
import logging
import ffmpeg
import tempfile
import ffmpeg

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
    
    def _validate_audio_file(self, audio_data: bytes, source_format: str) -> bool:
        """
        Validate audio file integrity using ffprobe
        
        Args:
            audio_data: Audio file binary data
            source_format: Source audio format
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=f'.{source_format}', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                temp_path = temp_file.name
            
            try:
                # Use ffprobe to validate the file
                probe = ffmpeg.probe(temp_path)
                
                # Check if we have audio streams
                audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
                if not audio_streams:
                    logger.warning(f"No audio streams found in {source_format} file")
                    return False
                
                # Log file information
                logger.info(f"Valid {source_format} file detected:")
                for stream in audio_streams:
                    codec = stream.get('codec_name', 'unknown')
                    duration = stream.get('duration', 'unknown')
                    sample_rate = stream.get('sample_rate', 'unknown')
                    channels = stream.get('channels', 'unknown')
                    logger.info(f"  Codec: {codec}, Duration: {duration}s, Sample Rate: {sample_rate}, Channels: {channels}")
                
                return True
                
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                    
        except Exception as e:
            logger.error(f"Audio file validation failed: {e}")
            return False

    def _convert_to_mp4_with_ffmpeg(self, audio_data: bytes, source_format: str) -> bytes:
        """
        Convert audio data to MP4 format using ffmpeg
        
        Args:
            audio_data: Original audio file binary data
            source_format: Source audio format (webm, ogg, etc.)
            
        Returns:
            MP4 audio binary data
        """
        try:
            # First validate the input file
            logger.info(f"Validating {source_format} file ({len(audio_data)} bytes)...")
            if not self._validate_audio_file(audio_data, source_format):
                logger.error(f"Invalid {source_format} file detected, skipping conversion")
                raise ValueError(f"Invalid {source_format} audio file")
            
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(suffix=f'.{source_format}', delete=False) as input_file:
                input_file.write(audio_data)
                input_file.flush()
                input_path = input_file.name
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as output_file:
                output_path = output_file.name
            
            try:
                logger.info(f"Starting conversion from {source_format} to MP4...")
                
                # Configure ffmpeg settings based on source format
                if source_format.lower() == 'webm':
                    # WebM specific settings - specify input format explicitly
                    input_stream = ffmpeg.input(input_path, f='webm')
                    output_options = {
                        'vn': None,  # No video
                        'c:a': 'aac',  # AAC audio codec for MP4
                        'b:a': '128k',  # Audio bitrate
                        'ar': 44100,  # Sample rate
                        'ac': 2,  # Stereo channels
                        'f': 'mp4',  # Force MP4 format
                        'movflags': 'frag_keyframe+empty_moov'  # Better MP4 compatibility
                    }
                else:
                    # For other formats
                    input_stream = ffmpeg.input(input_path)
                    output_options = {
                        'vn': None,  # No video
                        'c:a': 'aac',  # AAC audio codec for MP4
                        'b:a': '128k',  # Audio bitrate
                        'ar': 44100,  # Sample rate
                        'ac': 2,  # Stereo channels
                        'f': 'mp4'  # Force MP4 format
                    }
                
                # Convert using ffmpeg-python
                result = (
                    input_stream
                    .output(output_path, **output_options)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                # Check if output file was created and has content
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise RuntimeError("FFmpeg conversion produced empty output file")
                
                # Read the converted MP4 data
                with open(output_path, 'rb') as f:
                    mp4_data = f.read()
                
                logger.info(f"Successfully converted audio from {source_format} to MP4 using ffmpeg")
                logger.info(f"Original size: {len(audio_data)} bytes, Converted size: {len(mp4_data)} bytes")
                return mp4_data
                
            except ffmpeg.Error as e:
                # Log detailed ffmpeg error information
                stderr_output = e.stderr.decode('utf-8') if e.stderr else 'No stderr available'
                stdout_output = e.stdout.decode('utf-8') if e.stdout else 'No stdout available'
                logger.error(f"FFmpeg conversion failed:")
                logger.error(f"  Command: {' '.join(e.cmd) if hasattr(e, 'cmd') else 'Unknown command'}")
                logger.error(f"  Return code: {e.returncode if hasattr(e, 'returncode') else 'Unknown'}")
                logger.error(f"  STDERR: {stderr_output}")
                logger.error(f"  STDOUT: {stdout_output}")
                raise
                
            finally:
                # Clean up temporary files
                try:
                    os.unlink(input_path)
                    os.unlink(output_path)
                except OSError:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to convert audio from {source_format} to MP4 using ffmpeg: {e}")
            # Don't return original data if conversion fails - raise the error instead
            raise
    
    def upload_audio_file(
        self, 
        audio_data: bytes, 
        session_id: Optional[str] = None,
        audio_format: str = "mp4"
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
            
            # Convert to MP4 if source format is not MP4
            final_audio_data = audio_data
            final_format = "mp4"  # Always save as MP4
            
            if audio_format.lower() not in ["mp4", "m4a"]:
                logger.info(f"Converting audio from {audio_format} to MP4 using ffmpeg")
                final_audio_data = self._convert_to_mp4_with_ffmpeg(audio_data, audio_format)
            
            # Organize files by session if provided
            if session_id:
                blob_name = f"audio/{session_id}/{audio_id}_{timestamp}.{final_format}"
            else:
                blob_name = f"audio/{audio_id}_{timestamp}.{final_format}"
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload file with metadata
            blob_client.upload_blob(
                final_audio_data,
                overwrite=True,
                metadata={
                    'audio_id': audio_id,
                    'session_id': session_id or 'no-session',
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'format': final_format,
                    'original_format': audio_format
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
