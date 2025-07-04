"""
Azure OpenAI API用データ転送オブジェクト
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class AzureSessionRequest(BaseModel):
    """Azure OpenAI Sessions API リクエスト"""
    model: str = Field(..., description="Azure OpenAI deployment model name")
    voice: str = Field(..., description="Voice type for the AI assistant")
    instructions: Optional[str] = Field(
        "あなたはとても優秀なAIアシスタントです。会話内容に対して、非常にナチュラルな返事をします。",
        description="System instructions for the AI"
    )
    modalities: Optional[List[str]] = Field(
        default=["text", "audio"],
        description="Supported modalities"
    )
    tools: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Available tools for the AI"
    )


class AzureSessionResponse(BaseModel):
    """Azure OpenAI Sessions API レスポンス"""
    id: str = Field(..., description="Session ID")
    object: str = Field(..., description="Object type")
    model: str = Field(..., description="Model name")
    expires_at: Optional[int] = Field(None, description="Session expiration timestamp")
    client_secret: Optional[Dict[str, Any]] = Field(None, description="Client secret for WebRTC")


class AzureErrorResponse(BaseModel):
    """Azure OpenAI API エラーレスポンス"""
    error: Dict[str, Any] = Field(..., description="Error details from Azure OpenAI")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "InvalidRequestError",
                    "message": "The request is invalid",
                    "type": "invalid_request_error"
                }
            }
        }
