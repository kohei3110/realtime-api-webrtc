"""
FastAPI アプリケーション
"""
from fastapi import FastAPI
import uvicorn
import os

from presentation.middleware.cors_middleware import setup_cors_middleware
from presentation.api.controllers.health_controller import HealthController
from presentation.api.controllers.sessions_proxy_controller import SessionsProxyController
from presentation.api.controllers import audio_upload_controller
from shared.monitoring.health import HealthCheckService, SimpleHealthCheck
from shared.utils.logging import setup_logging, get_logger

# ログ設定
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(level=log_level, format_type="detailed")
logger = get_logger("main")


def create_app() -> FastAPI:
    """FastAPIアプリケーション作成"""
    logger.info("Creating FastAPI application...")
    
    app = FastAPI(
        title="Azure OpenAI Realtime API Proxy",
        description="Azure OpenAI Realtime API プロキシサーバー",
        version="0.1.0",
        # トレイリングスラッシュの有無に関わらず同じハンドラーを使用
        redirect_slashes=True
    )
    
    # CORS設定
    frontend_origins = [
        origin.strip() for origin in 
        os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    ]
    logger.info(f"Configuring CORS for origins: {frontend_origins}")
    setup_cors_middleware(app, frontend_origins)
    
    # ヘルスチェックサービス
    health_service = HealthCheckService(
        health_checks=[SimpleHealthCheck(name="api")]
    )
    
    # コントローラー登録
    logger.info("Registering API controllers...")
    health_controller = HealthController(health_service)
    app.include_router(health_controller.router)
    
    # プロキシコントローラー登録
    try:
        # 依存性注入を使用してコントローラーを作成
        sessions_controller = SessionsProxyController()
        app.include_router(sessions_controller.router)
        logger.info("Sessions proxy controller registered")
        
        # 音声アップロードコントローラー登録
        app.include_router(audio_upload_controller.router)
        logger.info("Audio upload controller registered")
        
    except Exception as e:
        logger.error(f"Failed to register proxy controllers: {e}")
        raise
    
    logger.info("FastAPI application created successfully")
    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Azure OpenAI Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT', 'Not configured')}")
    logger.info(f"API Version: {os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-01-preview')}")
    
    uvicorn.run("main:app", host=host, port=port, reload=True)
