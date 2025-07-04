"""
Azure OpenAI Sessions API プロキシコントローラー
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from application.interfaces.azure_proxy_service import IAzureProxyService
from infrastructure.configuration.dependencies import get_azure_proxy_service
from presentation.dto.proxy_dto import SessionCreateRequest, SessionCreateResponse, ErrorResponse
from shared.utils.logging import get_logger

logger = get_logger("sessions_proxy")


class SessionsProxyController:
    """Azure OpenAI Sessions API プロキシコントローラー
    
    フロントエンドからのセッション作成リクエストを受け取り、
    Azure OpenAI Realtime API にプロキシする責任を持ちます。
    """
    
    def __init__(self):
        """初期化"""
        self.router = APIRouter(prefix="/sessions", tags=["sessions-proxy"])
        self._setup_routes()
    
    def _setup_routes(self):
        """ルート設定"""
        self.router.add_api_route(
            "/",
            self.create_session_proxy,
            methods=["POST"],
            status_code=200,  # Azure APIに合わせて200に変更
            response_model=SessionCreateResponse,
            responses={
                400: {"model": ErrorResponse, "description": "Invalid request"},
                401: {"model": ErrorResponse, "description": "Authentication error"},
                429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
                502: {"model": ErrorResponse, "description": "Azure OpenAI API error"},
                500: {"model": ErrorResponse, "description": "Internal server error"}
            }
        )
    
    async def create_session_proxy(
        self,
        request: SessionCreateRequest,
        api_key: Optional[str] = Header(None, alias="api-key"),  # フロントエンドから受信するが無視
        azure_proxy_service: IAzureProxyService = Depends(get_azure_proxy_service)
    ) -> SessionCreateResponse:
        """Azure OpenAI Sessions API プロキシエンドポイント
        
        フロントエンドからのセッション作成リクエストを受け取り、
        Azure OpenAI Realtime API にプロキシします。
        
        Args:
            request: セッション作成リクエスト
            api_key: フロントエンドからのapi-keyヘッダー（使用しない）
            azure_proxy_service: Azure プロキシサービス
            
        Returns:
            Azure OpenAI APIからのセッション作成レスポンス
            
        Raises:
            HTTPException: プロキシ処理中のエラー
        """
        try:
            # フロントエンドからのapi-keyヘッダーは無視し、ログに記録
            if api_key:
                logger.debug("Received api-key header from frontend (ignored for security)")
            
            logger.info(f"Session creation request: model={request.model}, voice={request.voice}")
            
            # Azure プロキシサービスに処理を委譲
            response = await azure_proxy_service.create_session_proxy(request)
            
            logger.info(f"Session created successfully: {response.id}")
            return response
            
        except HTTPException:
            # HTTPExceptionはそのまま再発生
            raise
        except Exception as e:
            logger.error(f"Unexpected error in sessions proxy controller: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
