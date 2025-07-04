"""
Azure プロキシサービスインターフェース
"""
from abc import ABC, abstractmethod
from presentation.dto.proxy_dto import SessionCreateRequest, SessionCreateResponse


class IAzureProxyService(ABC):
    """Azure OpenAI プロキシサービスインターフェース"""
    
    @abstractmethod
    async def create_session_proxy(self, request: SessionCreateRequest) -> SessionCreateResponse:
        """セッション作成リクエストをAzure OpenAI APIにプロキシ
        
        Args:
            request: フロントエンドからのセッション作成リクエスト
            
        Returns:
            Azure OpenAI APIからのセッション作成レスポンス
            
        Raises:
            HTTPException: プロキシ処理中のエラー
        """
        pass
    
    @abstractmethod
    async def webrtc_sdp_proxy(self, model: str, ephemeral_key: str, sdp_offer: str) -> str:
        """WebRTC SDP Offer をAzure OpenAI APIにプロキシ
        
        Args:
            model: Azure OpenAI model name
            ephemeral_key: セッションからのephemeral key
            sdp_offer: WebRTC SDP Offer
            
        Returns:
            Azure OpenAI APIからのSDP Answer
            
        Raises:
            HTTPException: プロキシ処理中のエラー
        """
        pass
