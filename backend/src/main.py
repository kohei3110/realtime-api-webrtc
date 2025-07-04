"""
FastAPI アプリケーション
"""
from fastapi import FastAPI
import uvicorn
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み（プロジェクトルートの.envを探す）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from presentation.middleware.cors_middleware import setup_cors_middleware
from presentation.api.controllers.health_controller import HealthController
from shared.monitoring.health import HealthCheckService, SimpleHealthCheck


def create_app() -> FastAPI:
    """FastAPIアプリケーション作成"""
    app = FastAPI(
        title="Azure OpenAI Realtime API Proxy",
        description="Azure OpenAI Realtime API プロキシサーバー",
        version="0.1.0",
        # トレイリングスラッシュの有無に関わらず同じハンドラーを使用
        redirect_slashes=False
    )
    
    # CORS設定
    frontend_origins = [
        origin.strip() for origin in 
        os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    ]
    setup_cors_middleware(app, frontend_origins)
    
    # ヘルスチェックサービス
    health_service = HealthCheckService(
        health_checks=[SimpleHealthCheck(name="api")]
    )
    
    # コントローラー登録
    health_controller = HealthController(health_service)
    app.include_router(health_controller.router)
    
    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
