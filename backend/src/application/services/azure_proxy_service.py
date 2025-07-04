"""
Azure プロキシサービス実装
"""
from fastapi import HTTPException
from application.interfaces.azure_proxy_service import IAzureProxyService
from infrastructure.azure.azure_openai_client import IAzureOpenAIClient, AzureOpenAIException
from presentation.dto.proxy_dto import SessionCreateRequest, SessionCreateResponse
from application.dto.azure_dto import AzureSessionRequest
from shared.utils.logging import get_logger


class AzureProxyService(IAzureProxyService):
    """Azure OpenAI プロキシサービス実装
    
    フロントエンドのリクエストをAzure OpenAI APIに透過的にプロキシする責任を持ちます。
    エラーハンドリング、レスポンス変換、ログ記録を含みます。
    """
    
    def __init__(self, azure_client: IAzureOpenAIClient):
        """初期化
        
        Args:
            azure_client: Azure OpenAI クライアント
        """
        self.azure_client = azure_client
        self.logger = get_logger("azure_proxy_service")
    
    async def create_session_proxy(self, request: SessionCreateRequest) -> SessionCreateResponse:
        """セッション作成リクエストをAzure OpenAI APIにプロキシ"""
        try:
            self.logger.info(f"Proxying session creation for model: {request.model}")
            
            # フロントエンドのリクエストをAzure API形式に変換
            azure_request = AzureSessionRequest(
                model=request.model,
                voice=request.voice,
                instructions=request.instructions,
                modalities=request.modalities or ["text", "audio"],  # Noneの場合デフォルト値を使用
                tools=request.tools
            )
            
            # Azure OpenAI APIを呼び出し
            azure_response = await self.azure_client.create_session(azure_request)
            
            # レスポンスをフロントエンド形式に変換
            response = SessionCreateResponse(
                id=azure_response.id,
                object=azure_response.object,
                model=azure_response.model,
                expires_at=azure_response.expires_at,
                client_secret=azure_response.client_secret  # client_secretを含める
            )
            
            self.logger.info(f"Session proxy completed successfully: {response.id}")
            return response
            
        except AzureOpenAIException as e:
            self.logger.error(f"Azure OpenAI error during session creation: {str(e)}")
            
            # Azure APIエラーをHTTPエラーにマッピング
            if e.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid request parameters")
            elif e.status_code == 401:
                raise HTTPException(status_code=502, detail="Azure OpenAI authentication failed")
            elif e.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif e.status_code and 500 <= e.status_code < 600:
                raise HTTPException(status_code=502, detail="Azure OpenAI service unavailable")
            else:
                raise HTTPException(status_code=502, detail="Azure OpenAI API error")
                
        except Exception as e:
            self.logger.error(f"Unexpected error during session proxy: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def webrtc_sdp_proxy(self, model: str, ephemeral_key: str, sdp_offer: str) -> str:
        """WebRTC SDP Offer をAzure OpenAI APIにプロキシ"""
        try:
            self.logger.info(f"Proxying WebRTC SDP for model: {model}")
            
            # ephemeral keyの形式検証
            if not ephemeral_key or not ephemeral_key.startswith("ek_"):
                self.logger.error("Invalid ephemeral key format")
                raise HTTPException(status_code=400, detail="Invalid ephemeral key format")
            
            # SDP Offerの基本検証
            if not sdp_offer or "v=0" not in sdp_offer:
                self.logger.error("Invalid SDP format")
                raise HTTPException(status_code=400, detail="Invalid SDP format")
            
            # Azure OpenAI APIを呼び出し
            sdp_answer = await self.azure_client.proxy_webrtc_sdp(model, ephemeral_key, sdp_offer)
            
            self.logger.info("WebRTC SDP proxy completed successfully")
            return sdp_answer
            
        except AzureOpenAIException as e:
            self.logger.error(f"Azure OpenAI error during WebRTC proxy: {str(e)}")
            
            # Azure APIエラーをHTTPエラーにマッピング
            if e.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid ephemeral key")
            elif e.status_code == 400:
                raise HTTPException(status_code=400, detail="Invalid WebRTC request")
            elif e.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            elif e.status_code and 500 <= e.status_code < 600:
                raise HTTPException(status_code=502, detail="Azure WebRTC service unavailable")
            else:
                raise HTTPException(status_code=502, detail="Azure WebRTC API error")
                
        except HTTPException:
            raise  # 既にHTTPExceptionの場合はそのまま再発生
        except Exception as e:
            self.logger.error(f"Unexpected error during WebRTC proxy: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
