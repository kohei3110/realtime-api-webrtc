"""
依存性注入設定
"""
import os
from typing import Optional
from application.interfaces.azure_proxy_service import IAzureProxyService
from application.services.azure_proxy_service import AzureProxyService
from infrastructure.azure.azure_openai_client import IAzureOpenAIClient, AzureOpenAIClient
from shared.utils.logging import get_logger

logger = get_logger("dependency_injection")


def create_azure_openai_client() -> IAzureOpenAIClient:
    """Azure OpenAI クライアントを作成
    
    Returns:
        設定されたAzure OpenAI クライアント
        
    Raises:
        ValueError: 必要な環境変数が設定されていない場合
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
    
    if not endpoint:
        raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
    if not api_key:
        raise ValueError("AZURE_OPENAI_API_KEY environment variable is required")
    
    logger.info(f"Creating Azure OpenAI client for endpoint: {endpoint}")
    
    return AzureOpenAIClient(
        endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        timeout=float(os.getenv("AZURE_OPENAI_TIMEOUT", "30.0")),
        max_retries=int(os.getenv("AZURE_OPENAI_MAX_RETRIES", "3"))
    )


def create_azure_proxy_service(azure_client: Optional[IAzureOpenAIClient] = None) -> IAzureProxyService:
    """Azure プロキシサービスを作成
    
    Args:
        azure_client: Azure OpenAI クライアント（省略時は自動作成）
        
    Returns:
        設定されたAzure プロキシサービス
    """
    if azure_client is None:
        azure_client = create_azure_openai_client()
    
    logger.info("Creating Azure proxy service")
    return AzureProxyService(azure_client)


# グローバルインスタンス（シングルトン）
_azure_proxy_service: Optional[IAzureProxyService] = None


def get_azure_proxy_service() -> IAzureProxyService:
    """Azure プロキシサービスのシングルトンインスタンスを取得
    
    Returns:
        Azure プロキシサービス
    """
    global _azure_proxy_service
    
    if _azure_proxy_service is None:
        _azure_proxy_service = create_azure_proxy_service()
        logger.info("Azure proxy service singleton created")
    
    return _azure_proxy_service


def reset_dependencies():
    """依存関係をリセット（主にテスト用）"""
    global _azure_proxy_service
    _azure_proxy_service = None
    logger.info("Dependencies reset")
