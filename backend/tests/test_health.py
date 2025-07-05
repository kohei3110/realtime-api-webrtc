"""
ヘルスエンドポイントのテスト
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """テスト用クライアント"""
    return TestClient(app)


def test_health_check(client):
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "checks" in data
    assert "api" in data["checks"]
    assert data["checks"]["api"]["status"] == "healthy"
