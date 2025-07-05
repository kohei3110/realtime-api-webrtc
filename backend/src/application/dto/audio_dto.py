from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class AudioMetadata(BaseModel):
    """音声メタデータモデル"""
    audio_type: str = "user_speech"
    format: str = "webm"
    duration: float = 0.0
    sample_rate: int = 48000
    channels: int = 1
    timestamp_start: Optional[str] = None
    timestamp_end: Optional[str] = None
    language: str = "ja-JP"


class AudioUploadResponse(BaseModel):
    """音声アップロードレスポンスモデル"""
    audio_id: str
    session_id: Optional[str]
    audio_type: str
    blob_url: str
    sas_url: Optional[str]
    sas_expires_at: Optional[datetime]
    size_bytes: int
    metadata: AudioMetadata
    uploaded_at: datetime
