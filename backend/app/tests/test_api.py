"""API integration tests — hermetic, backed by in-memory SQLite (see conftest)."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "stock-analyze-api"
    # /health probes the real engine directly; in CI there is no Postgres,
    # so "degraded" (db down) is acceptable — the endpoint must not 500.
    assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_stock_search_empty(client, monkeypatch):
    # Empty search triggers the stock-list self-heal; stub it out so the
    # test stays offline.
    from app.services import ondemand

    async def _no_seed(db):
        return 0

    monkeypatch.setattr(ondemand, "ensure_stock_list", _no_seed)
    response = await client.get("/api/v1/stocks/search?q=2330")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_stock_not_found(client):
    response = await client.get("/api/v1/stocks/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_news_market(client):
    response = await client.get("/api/v1/news/market")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_screener_empty(client):
    response = await client.get("/api/v1/analysis/screener")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_watchlist_requires_auth(client):
    response = await client.get("/api/v1/watchlist")
    assert response.status_code in (401, 403)
