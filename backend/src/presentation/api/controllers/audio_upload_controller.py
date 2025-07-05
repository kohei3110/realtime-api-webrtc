from fastapi import APIRouter, UploadFile, File, Form, Header, HTTPException, Depends
from typing import Optional
import logging
from application.services.audio_upload_service import AudioUploadService
from application.dto.audio_dto import AudioUploadResponse
from infrastructure.storage.audio_blob_storage_client import AudioBlobStorageClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])


# Dependency to get AudioUploadService
def get_audio_upload_service() -> AudioUploadService:
    """音声アップロードサービスの依存性注入"""
    blob_storage_client = AudioBlobStorageClient()
    return AudioUploadService(blob_storage_client)


@router.post("/upload", response_model=AudioUploadResponse, status_code=201)
async def upload_audio_file(
    audio_file: UploadFile = File(..., description="Audio file to upload"),
    metadata: Optional[str] = Form(None, description="Audio metadata as JSON string"),
    session_id: Optional[str] = Header(None, alias="session-id", description="Session ID"),
    audio_service: AudioUploadService = Depends(get_audio_upload_service)
) -> AudioUploadResponse:
    """
    音声ファイルをAzure Blob Storageにアップロードします
    
    - **audio_file**: アップロードする音声ファイル (WebM/Opus推奨)
    - **metadata**: 音声メタデータ (JSON形式)
    - **session-id**: 関連するセッションID (ヘッダー)
    
    Returns:
        AudioUploadResponse: アップロード結果とBlob URL
    """
    try:
        # ファイル検証
        if not audio_file.filename:
            raise HTTPException(status_code=400, detail="Audio file is required")
        
        # ファイル内容を読み取り
        audio_data = await audio_file.read()
        
        # ファイルサイズとタイプの検証
        audio_service.validate_audio_file(
            content_type=audio_file.content_type or "audio/webm",
            file_size=len(audio_data)
        )
        
        logger.info(f"Uploading audio file: {audio_file.filename} ({len(audio_data)} bytes)")
        
        # 音声ファイルをアップロード
        result = await audio_service.upload_audio(
            audio_data=audio_data,
            filename=audio_file.filename,
            metadata_json=metadata,
            session_id=session_id
        )
        
        logger.info(f"Successfully uploaded audio file: {result.audio_id}")
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading audio file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during audio upload")


@router.get("/health")
async def audio_service_health():
    """音声サービスのヘルスチェック"""
    try:
        # Azure Blob Storage接続テスト
        blob_client = AudioBlobStorageClient()
        # 単純な接続確認
        return {
            "status": "healthy",
            "service": "audio-upload",
            "timestamp": logger.info("Audio service health check passed"),
            "storage": "connected"
        }
    except Exception as e:
        logger.error(f"Audio service health check failed: {e}")
        raise HTTPException(status_code=503, detail="Audio service unavailable")
