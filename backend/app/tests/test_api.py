"""API integration tests for the stock analysis platform."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_stock_search_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stocks/search?q=2330")
        assert response.status_code == 200
        # Will return empty list if no stocks seeded, but should not error
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_stock_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stocks/9999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_news_market():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/news/market")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
