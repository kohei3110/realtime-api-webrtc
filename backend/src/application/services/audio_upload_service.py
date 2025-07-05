import json
import logging
from typing import Optional
from datetime import datetime
from application.dto.audio_dto import AudioMetadata, AudioUploadResponse
from infrastructure.storage.audio_blob_storage_client import AudioBlobStorageClient

logger = logging.getLogger(__name__)


class AudioUploadService:
    """音声アップロードサービス"""
    
    def __init__(self, blob_storage_client: AudioBlobStorageClient):
        self.blob_storage_client = blob_storage_client
    
    async def upload_audio(
        self,
        audio_data: bytes,
        filename: str,
        metadata_json: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AudioUploadResponse:
        """
        音声ファイルをアップロードします
        
        Args:
            audio_data: 音声ファイルのバイナリデータ
            filename: ファイル名
            metadata_json: メタデータのJSON文字列
            session_id: セッションID
            
        Returns:
            AudioUploadResponse: アップロード結果
        """
        try:
            # ファイル形式を抽出
            audio_format = self._extract_format(filename)
            
            # メタデータを解析
            metadata = self._parse_metadata(metadata_json)
            
            # Blob Storageにアップロード
            try:
                audio_id, blob_url = self.blob_storage_client.upload_audio_file(
                    audio_data=audio_data,
                    session_id=session_id,
                    audio_format=audio_format
                )
            except ValueError as ve:
                # Audio file validation or conversion failed
                logger.error(f"Audio file processing failed: {ve}")
                raise ValueError(f"Audio file is invalid or corrupted: {ve}")
            except Exception as e:
                # Other upload errors
                logger.error(f"Audio upload failed: {e}")
                raise RuntimeError(f"Failed to upload audio file: {e}")
            
            # SAS URLを生成
            sas_url, sas_expires_at = self.blob_storage_client.generate_sas_url(
                blob_url=blob_url,
                expire_hours=1
            )
            
            # レスポンスを構築
            response = AudioUploadResponse(
                audio_id=audio_id,
                session_id=session_id,
                audio_type=metadata.audio_type,
                blob_url=blob_url,
                sas_url=sas_url,
                sas_expires_at=sas_expires_at,
                size_bytes=len(audio_data),
                metadata=metadata,
                uploaded_at=datetime.utcnow()
            )
            
            logger.info(f"Successfully uploaded audio: {audio_id}")
            return response
            
        except (ValueError, RuntimeError):
            # Re-raise specific errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading audio: {e}")
            raise RuntimeError(f"Audio upload service error: {e}")
    
    def _extract_format(self, filename: str) -> str:
        """ファイル名から形式を抽出"""
        if '.' in filename:
            return filename.split('.')[-1].lower()
        return 'webm'  # デフォルト
    
    def _parse_metadata(self, metadata_json: Optional[str]) -> AudioMetadata:
        """メタデータJSONを解析"""
        current_time = datetime.utcnow().isoformat()
        
        # デフォルト値
        default_metadata = {
            "audio_type": "user_speech",
            "format": "webm",
            "duration": 0.0,
            "sample_rate": 48000,
            "channels": 1,
            "timestamp_start": current_time,
            "timestamp_end": current_time,
            "language": "ja-JP"
        }
        
        if not metadata_json:
            # デフォルトメタデータ
            return AudioMetadata(**default_metadata)
        
        try:
            metadata_dict = json.loads(metadata_json)
            
            # デフォルト値でNoneや欠落値を補完
            for key, default_value in default_metadata.items():
                if key not in metadata_dict or metadata_dict[key] is None:
                    metadata_dict[key] = default_value
            
            return AudioMetadata(**metadata_dict)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Invalid metadata JSON, using defaults: {e}")
            return AudioMetadata(**default_metadata)
    
    def validate_audio_file(self, content_type: str, file_size: int) -> None:
        """音声ファイルを検証"""
        # ファイルサイズチェック (100MB制限)
        max_size = 100 * 1024 * 1024  # 100MB
        if file_size > max_size:
            raise ValueError(f"File size ({file_size} bytes) exceeds maximum limit ({max_size} bytes)")
        
        # コンテンツタイプチェック
        allowed_types = [
            'audio/webm',
            'audio/opus',
            'audio/wav',
            'audio/mpeg',
            'audio/mp4'
        ]
        
        if content_type not in allowed_types:
            logger.warning(f"Content type {content_type} not in allowed list, but proceeding")
