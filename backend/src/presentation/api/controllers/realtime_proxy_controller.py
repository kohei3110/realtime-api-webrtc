"""
Azure OpenAI WebRTC API プロキシコントローラー
"""
from fastapi import APIRouter, HTTPException, Header, Request, Query
from starlette.responses import Response
import aiohttp
import os

from shared.utils.logging import get_logger

logger = get_logger("realtime_proxy")


class RealtimeProxyController:
    """Azure OpenAI WebRTC API プロキシコントローラー"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/realtime", tags=["realtime-proxy"])
        self._setup_routes()
        
        # Azure OpenAI設定
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
        
        if not self.azure_endpoint:
            raise ValueError("Azure OpenAI endpoint must be configured")
    
    def _setup_routes(self):
        """ルート設定"""
        self.router.add_api_route("/", self.webrtc_sdp_proxy, methods=["POST"])
    
    async def webrtc_sdp_proxy(
        self,
        request: Request,
        model: str = Query(..., description="AI model name"),
        authorization: str = Header(..., alias="Authorization")
    ) -> Response:
        """Azure OpenAI WebRTC SDP プロキシエンドポイント"""
        try:
            # Bearer tokenからephemeral_keyを抽出
            if not authorization.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authorization header format")
            
            ephemeral_key = authorization[7:]  # "Bearer "を除去
            logger.info(f"WebRTC SDP proxy request: model={model}")
            
            # SDP Offer取得
            sdp_offer = await request.body()
            sdp_offer_text = sdp_offer.decode('utf-8')
            
            # SDP形式の基本的な検証
            if not sdp_offer_text.strip().startswith('v='):
                raise HTTPException(status_code=400, detail="Invalid SDP format: must start with 'v=' line")
            
            logger.info(f"Received SDP offer with {len(sdp_offer_text)} characters")
            
            # Azure OpenAI WebRTC APIにプロキシ
            async with aiohttp.ClientSession() as session:
                azure_url = f"{self.azure_endpoint}/openai/realtime"
                headers = {
                    "Authorization": f"Bearer {ephemeral_key}",
                    "Content-Type": "application/sdp"
                }
                params = {
                    "model": model,
                    "api-version": self.api_version
                }
                
                logger.info(f"Calling Azure OpenAI WebRTC API: {azure_url}")
                
                async with session.post(
                    azure_url,
                    headers=headers,
                    params=params,
                    data=sdp_offer_text
                ) as response:
                    sdp_answer = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Azure WebRTC API failed: {response.status} - {sdp_answer}")
                        raise HTTPException(
                            status_code=502, 
                            detail=f"Azure WebRTC API error: {response.status}"
                        )
                    
                    logger.info(f"Received SDP answer with {len(sdp_answer)} characters")
                    
                    # SDP Answerの基本的な検証
                    if not sdp_answer.strip().startswith('v='):
                        logger.error("Invalid SDP answer format from Azure")
                        raise HTTPException(status_code=502, detail="Invalid SDP answer from Azure API")
                    
                    return Response(content=sdp_answer, media_type="application/sdp")
                    
        except HTTPException:
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Azure WebRTC API connection error: {str(e)}")
            raise HTTPException(status_code=502, detail="Failed to connect to Azure WebRTC API")
        except Exception as e:
            logger.error(f"WebRTC API proxy error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
