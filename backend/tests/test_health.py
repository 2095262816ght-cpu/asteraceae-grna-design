import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app


@pytest.mark.anyio
async def test_health_check_returns_ok_and_database_status():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["database"] == "connected"
    assert "timestamp" in data
