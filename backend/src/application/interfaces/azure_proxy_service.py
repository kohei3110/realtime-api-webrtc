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
