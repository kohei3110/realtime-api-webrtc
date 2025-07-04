"""
セッション作成プロキシサービスのユニットテスト
"""
import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException

from application.services.azure_proxy_service import AzureProxyService
from infrastructure.azure.azure_openai_client import AzureOpenAIException
from presentation.dto.proxy_dto import SessionCreateRequest, SessionCreateResponse
from application.dto.azure_dto import AzureSessionResponse


@pytest.mark.asyncio
class TestAzureProxyService:
    """Azure プロキシサービスのテスト"""
    
    def setup_method(self):
        """テストセットアップ"""
        self.mock_azure_client = AsyncMock()
        self.service = AzureProxyService(self.mock_azure_client)
    
    async def test_create_session_proxy_success(self):
        """セッション作成プロキシの正常ケース"""
        # Arrange
        request = SessionCreateRequest(
            model="gpt-4o-realtime-preview",
            voice="alloy"
        )
        
        azure_response = AzureSessionResponse(
            id="sess_test123",
            object="realtime.session",
            model="gpt-4o-realtime-preview",
            expires_at=1704067200
        )
        
        self.mock_azure_client.create_session.return_value = azure_response
        
        # Act
        result = await self.service.create_session_proxy(request)
        
        # Assert
        assert isinstance(result, SessionCreateResponse)
        assert result.id == "sess_test123"
        assert result.model == "gpt-4o-realtime-preview"
        self.mock_azure_client.create_session.assert_called_once()
    
    async def test_create_session_proxy_azure_auth_error(self):
        """Azure認証エラーの場合"""
        # Arrange
        request = SessionCreateRequest(
            model="gpt-4o-realtime-preview",
            voice="alloy"
        )
        
        self.mock_azure_client.create_session.side_effect = AzureOpenAIException(
            "Authentication failed", status_code=401
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_session_proxy(request)
        
        assert exc_info.value.status_code == 502
        assert "Azure OpenAI authentication failed" in str(exc_info.value.detail)
    
    async def test_create_session_proxy_rate_limit_error(self):
        """レート制限エラーの場合"""
        # Arrange
        request = SessionCreateRequest(
            model="gpt-4o-realtime-preview",
            voice="alloy"
        )
        
        self.mock_azure_client.create_session.side_effect = AzureOpenAIException(
            "Rate limit exceeded", status_code=429
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_session_proxy(request)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)
    
    async def test_create_session_proxy_invalid_request(self):
        """無効なリクエストの場合"""
        # Arrange
        request = SessionCreateRequest(
            model="gpt-4o-realtime-preview",
            voice="alloy"
        )
        
        self.mock_azure_client.create_session.side_effect = AzureOpenAIException(
            "Invalid request", status_code=400
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.service.create_session_proxy(request)
        
        assert exc_info.value.status_code == 400
        assert "Invalid request parameters" in str(exc_info.value.detail)
    
    async def test_webrtc_sdp_proxy_success(self):
        """WebRTC SDP プロキシの正常ケース"""
        # Arrange
        model = "gpt-4o-realtime-preview"
        ephemeral_key = "ek_test123"
        sdp_offer = "v=0\no=- 1234567890 1234567890 IN IP4 127.0.0.1\n"
        sdp_answer = "v=0\no=- 0987654321 0987654321 IN IP4 20.12.34.56\n"
        
        self.mock_azure_client.proxy_webrtc_sdp.return_value = sdp_answer
        
        # Act
        result = await self.service.webrtc_sdp_proxy(model, ephemeral_key, sdp_offer)
        
        # Assert
        assert result == sdp_answer
        self.mock_azure_client.proxy_webrtc_sdp.assert_called_once_with(
            model, ephemeral_key, sdp_offer
        )
    
    async def test_webrtc_sdp_proxy_invalid_ephemeral_key(self):
        """無効なephemeral keyの場合"""
        # Arrange
        model = "gpt-4o-realtime-preview"
        ephemeral_key = "invalid_key"  # ek_ で始まらない
        sdp_offer = "v=0\no=- 1234567890 1234567890 IN IP4 127.0.0.1\n"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.service.webrtc_sdp_proxy(model, ephemeral_key, sdp_offer)
        
        assert exc_info.value.status_code == 400
        assert "Invalid ephemeral key format" in str(exc_info.value.detail)
    
    async def test_webrtc_sdp_proxy_invalid_sdp(self):
        """無効なSDPの場合"""
        # Arrange
        model = "gpt-4o-realtime-preview"
        ephemeral_key = "ek_test123"
        sdp_offer = "invalid sdp"  # v=0 が含まれていない
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await self.service.webrtc_sdp_proxy(model, ephemeral_key, sdp_offer)
        
        assert exc_info.value.status_code == 400
        assert "Invalid SDP format" in str(exc_info.value.detail)
