"""
ヘルスチェック機能
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time
from datetime import datetime
import asyncio


class HealthStatus(str, Enum):
    """ヘルスステータス"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """ヘルスチェック結果"""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


class IHealthCheck(ABC):
    """ヘルスチェックインターフェース"""
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        pass


class SimpleHealthCheck(IHealthCheck):
    """シンプルなヘルスチェック（常にhealthy）"""
    
    def __init__(self, name: str = "app"):
        self._name = name
    
    async def check(self) -> HealthCheckResult:
        """常にhealthy"""
        return HealthCheckResult(
            name=self._name,
            status=HealthStatus.HEALTHY,
            message="Service is running",
            response_time_ms=0.0
        )


class HealthCheckService:
    """ヘルスチェックサービス"""
    
    def __init__(self, health_checks: Optional[List[IHealthCheck]] = None):
        self._health_checks = health_checks or [SimpleHealthCheck()]
    
    async def check_all(self) -> Dict[str, Any]:
        """全ヘルスチェック実行"""
        results = await asyncio.gather(
            *[check.check() for check in self._health_checks],
            return_exceptions=True
        )
        
        overall_status = HealthStatus.HEALTHY
        check_results = {}
        
        for result in results:
            if isinstance(result, Exception):
                overall_status = HealthStatus.UNHEALTHY
                continue
            
            check_results[result.name] = {
                "status": result.status.value,
                "message": result.message,
                "response_time_ms": result.response_time_ms
            }
            
            if result.details:
                check_results[result.name]["details"] = result.details
            
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": check_results
        }
