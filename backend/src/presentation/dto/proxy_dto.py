"""
プロキシAPI用データ転送オブジェクト
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class SessionCreateRequest(BaseModel):
    """セッション作成リクエスト"""
    model: str = Field(..., description="Azure OpenAI deployment model name")
    voice: str = Field(..., description="Voice type for the AI assistant")
    instructions: Optional[str] = Field(None, description="System instructions for the AI")
    modalities: Optional[List[str]] = Field(None, description="Supported modalities")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-4o-realtime-preview",
                "voice": "alloy",
                "instructions": "あなたはとても優秀なAIアシスタントです。",
                "modalities": ["text", "audio"],
                "tools": []
            }
        }


class SessionCreateResponse(BaseModel):
    """セッション作成レスポンス"""
    id: str = Field(..., description="Session ID")
    object: str = Field(..., description="Object type")
    model: str = Field(..., description="Model name")
    expires_at: Optional[int] = Field(None, description="Session expiration timestamp")
    client_secret: Optional[Dict[str, Any]] = Field(None, description="Client secret for WebRTC connection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sess_001T4brAO1EhxMhTN6DbHEEW",
                "object": "realtime.session",
                "model": "gpt-4o-realtime-preview",
                "expires_at": 1704067200,
                "client_secret": {
                    "value": "ek_001T4bkjBqkGVq8ysnKjLAOU",
                    "expires_at": 1751629158
                }
            }
        }


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: Dict[str, Any] = Field(..., description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "type": "invalid_request_error",
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "Missing required field: model"
                }
            }
        }
