"""
Azure OpenAI Sessions API プロキシコントローラー
"""
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from typing import Optional
import aiohttp
import os
import json

from shared.utils.logging import get_logger

logger = get_logger("sessions_proxy")


class SessionsProxyController:
    """Azure OpenAI Sessions API プロキシコントローラー"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/sessions", tags=["sessions-proxy"])
        self._setup_routes()
        
        # Azure OpenAI設定
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
        
        if not self.azure_endpoint or not self.azure_api_key:
            raise ValueError("Azure OpenAI endpoint and API key must be configured")
    
    def _setup_routes(self):
        """ルート設定"""
        self.router.add_api_route("/", self.create_session_proxy, methods=["POST"], status_code=201)
    
    async def create_session_proxy(
        self,
        request: Request,
        api_key: Optional[str] = Header(None, alias="api-key")  # フロントエンドから受信するが無視
    ) -> dict:
        """Azure OpenAI Sessions API プロキシエンドポイント"""
        try:
            # リクエストボディを取得
            request_body = await request.json()
            logger.info(f"Sessions proxy request: {request_body}")
            
            # 必須フィールドの検証
            if "model" not in request_body:
                raise HTTPException(status_code=400, detail="Missing required field: model")
            if "voice" not in request_body:
                raise HTTPException(status_code=400, detail="Missing required field: voice")
            
            # Azure OpenAI Sessions APIに送信するリクエストを構築
            azure_request = {
                "model": request_body["model"],
                "voice": request_body["voice"],
                "instructions": "あなたはとても優秀なAIアシスタントです。会話内容に対して、非常にナチュラルな返事をします。",
                "modalities": ["text", "audio"],
                "tools": [
                    {
                        "type": "function",
                        "name": "changeBackgroundColor",
                        "description": "Changes the background color of a web page",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "color": {"type": "string", "description": "A hex value of the color"}
                            },
                            "required": ["color"]
                        }
                    },
                    {
                        "type": "function",
                        "name": "getPageHTML",
                        "description": "Gets the HTML for the current page"
                    },
                    {
                        "type": "function",
                        "name": "changeTextColor",
                        "description": "Changes the text color of a web page",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "color": {"type": "string", "description": "A hex value of the color"}
                            },
                            "required": ["color"]
                        }
                    }
                ]
            }
            
            # Azure OpenAI Sessions APIを呼び出し
            async with aiohttp.ClientSession() as session:
                azure_url = f"{self.azure_endpoint}/openai/realtime/sessions"
                headers = {
                    "api-key": self.azure_api_key,
                    "Content-Type": "application/json"
                }
                params = {
                    "api-version": self.api_version
                }
                
                logger.info(f"Calling Azure OpenAI Sessions API: {azure_url}")
                
                async with session.post(
                    azure_url,
                    headers=headers,
                    params=params,
                    json=azure_request
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 201:
                        logger.error(f"Azure OpenAI session creation failed: {response.status} - {response_text}")
                        raise HTTPException(
                            status_code=502, 
                            detail=f"Azure OpenAI Sessions API error: {response.status}"
                        )
                    
                    azure_response = json.loads(response_text)
                    logger.info(f"Azure session created successfully: {azure_response.get('id')}")
                    
                    return azure_response
                    
        except HTTPException:
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        except aiohttp.ClientError as e:
            logger.error(f"Azure OpenAI API connection error: {str(e)}")
            raise HTTPException(status_code=502, detail="Failed to connect to Azure OpenAI API")
        except Exception as e:
            logger.error(f"Sessions API proxy error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")
