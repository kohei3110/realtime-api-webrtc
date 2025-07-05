"""
ヘルスチェックコントローラー
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from shared.monitoring.health import HealthCheckService


class HealthController:
    """ヘルスチェックコントローラー"""
    
    def __init__(self, health_check_service: HealthCheckService):
        self._health_check_service = health_check_service
        self.router = APIRouter(prefix="/health", tags=["health"])
        self._setup_routes()
    
    def _setup_routes(self):
        """ルート設定"""
        # スラッシュありとなしの両方のパスを追加
        self.router.add_api_route("/", self.health_check, methods=["GET"])
        self.router.add_api_route("", self.health_check, methods=["GET"])
    
    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェックエンドポイント"""
        result = await self._health_check_service.check_all()
        
        if result["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=result)
        elif result["status"] == "degraded":
            return JSONResponse(status_code=200, content=result)
        else:
            return result
