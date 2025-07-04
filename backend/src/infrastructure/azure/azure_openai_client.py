"""
Azure OpenAI クライアントインターフェース
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from application.dto.azure_dto import AzureSessionRequest, AzureSessionResponse


class IAzureOpenAIClient(ABC):
    """Azure OpenAI クライアントインターフェース"""
    
    @abstractmethod
    async def create_session(self, request: AzureSessionRequest) -> AzureSessionResponse:
        """セッションを作成する
        
        Args:
            request: セッション作成リクエスト
            
        Returns:
            セッション作成レスポンス
            
        Raises:
            AzureOpenAIException: Azure API エラー
            ConnectionError: 接続エラー
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Azure OpenAI APIの接続確認
        
        Returns:
            ヘルスチェック結果
        """
        pass


import aiohttp
import asyncio
import os
import json
from typing import Dict, Any, Optional
from application.dto.azure_dto import AzureSessionRequest, AzureSessionResponse
from shared.utils.logging import get_logger


class AzureOpenAIException(Exception):
    """Azure OpenAI API 例外"""
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class AzureOpenAIClient(IAzureOpenAIClient):
    """Azure OpenAI クライアント実装
    
    Azure OpenAI Realtime API との通信を担当します。
    エラーハンドリング、リトライ、接続管理を含みます。
    """
    
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        api_version: str = "2024-10-01-preview",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """初期化
        
        Args:
            endpoint: Azure OpenAI エンドポイント
            api_key: Azure OpenAI API キー
            api_version: API バージョン
            timeout: タイムアウト秒数
            max_retries: 最大リトライ回数
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.api_version = api_version
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.logger = get_logger("azure_openai_client")
        
        # 接続プール設定（遅延初期化）
        self._connector = None
        self._timeout_seconds = timeout
    
    @property
    def connector(self) -> aiohttp.TCPConnector:
        """HTTPコネクターを遅延初期化で取得"""
        if self._connector is None:
            self._connector = aiohttp.TCPConnector(
                limit=100,  # 最大接続数
                limit_per_host=30,  # ホストあたりの最大接続数
                ttl_dns_cache=300,  # DNS キャッシュTTL (5分)
                use_dns_cache=True,
            )
        return self._connector
    
    async def create_session(self, request: AzureSessionRequest) -> AzureSessionResponse:
        """セッションを作成する"""
        # フロントエンドと同じエンドポイント形式を使用
        url = f"{self.endpoint}/openai/realtimeapi/sessions"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        params = {"api-version": self.api_version}
        
        # フロントエンドと同じリクエスト形式を使用
        request_data = {
            "model": request.model,
            "voice": request.voice
        }
        
        # 任意項目を追加
        if request.instructions:
            request_data["instructions"] = request.instructions
        if request.modalities:
            request_data["modalities"] = request.modalities
        if request.tools:
            request_data["tools"] = request.tools
        
        self.logger.info(f"Creating session with model: {request.model}")
        self.logger.info(f"Request URL: {url}")
        self.logger.info(f"Request params: {params}")
        self.logger.info(f"Request data: {json.dumps(request_data, ensure_ascii=False)}")
        
        try:
            # 新しいコネクターを毎回作成して接続問題を回避
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                enable_cleanup_closed=True
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout
            ) as session:
                async with session.post(
                    url,
                    headers=headers,
                    params=params,
                    json=request_data
                ) as response:
                    response_data = await self._handle_response(response)
                    
                    self.logger.info(f"Session created successfully: {response_data.get('id')}")
                    return AzureSessionResponse(**response_data)
                    
        except aiohttp.ClientError as e:
            error_msg = f"Azure OpenAI connection error: {str(e)}"
            self.logger.error(error_msg)
            raise AzureOpenAIException(error_msg)
        except asyncio.TimeoutError:
            error_msg = "Azure OpenAI request timeout"
            self.logger.error(error_msg)
            raise AzureOpenAIException(error_msg)
    
    async def health_check(self) -> Dict[str, Any]:
        """Azure OpenAI APIの接続確認"""
        try:
            # 軽量なヘルスチェック用のリクエスト
            url = f"{self.endpoint}/openai/models"
            headers = {"api-key": self.api_key}
            params = {"api-version": self.api_version}
            
            async with aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=10.0)  # ヘルスチェックは短いタイムアウト
            ) as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return {
                            "status": "healthy",
                            "azure_openai": "connected",
                            "endpoint": self.endpoint
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "azure_openai": f"error_{response.status}",
                            "endpoint": self.endpoint
                        }
        except Exception as e:
            self.logger.error(f"Azure OpenAI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "azure_openai": f"connection_error: {str(e)}",
                "endpoint": self.endpoint
            }
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """レスポンス処理とエラーハンドリング"""
        response_text = await response.text()
        
        if 200 <= response.status < 300:  # 成功（200, 201, 202など）
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON response from Azure OpenAI: {str(e)}"
                self.logger.error(error_msg)
                raise AzureOpenAIException(error_msg)
        else:
            # エラーレスポンスの解析
            try:
                error_data = json.loads(response_text)
                error_msg = error_data.get("error", {}).get("message", response_text)
                error_code = error_data.get("error", {}).get("code")
            except json.JSONDecodeError:
                error_msg = response_text
                error_code = None
            
            self.logger.error(f"Azure OpenAI API error: {response.status} - {error_msg}")
            raise AzureOpenAIException(error_msg, status_code=response.status, error_code=error_code)
    
    def _get_default_tools(self) -> list:
        """デフォルトのツール設定を取得"""
        return [
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
    
    async def __aenter__(self):
        """非同期コンテキストマネージャー入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー出口"""
        if self._connector:
            await self._connector.close()
