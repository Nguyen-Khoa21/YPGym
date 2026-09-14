import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_local_expo_web_origin_is_allowed():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Origin": "http://localhost:8081"},
    ) as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:8081"


@pytest.mark.asyncio
async def test_unknown_origin_is_not_allowed():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Origin": "http://malicious.example"},
    ) as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
