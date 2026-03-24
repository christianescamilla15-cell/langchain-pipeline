"""Tests for the analysis service."""
import pytest
from httpx import AsyncClient, ASGITransport
from services.analysis_service.main import app, _analyses


@pytest.fixture(autouse=True)
def clear_analyses():
    _analyses.clear()
    yield
    _analyses.clear()


@pytest.mark.asyncio
async def test_analyze_full_mode(sample_contract):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/analyze", json={
            "content": sample_contract,
            "mode": "full",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "full"
        assert "analysis" in data
        assert "tools" in data
        assert "keywords" in data["tools"]


@pytest.mark.asyncio
async def test_analyze_quick_mode(sample_financial):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/analyze", json={
            "content": sample_financial,
            "mode": "quick",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "quick"
        assert "summary" in data


@pytest.mark.asyncio
async def test_list_analyses(sample_contract):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/analyze", json={
            "content": sample_contract,
            "mode": "quick",
        })
        resp = await client.get("/analyses")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_get_analysis_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyses/nonexistent")
        assert resp.status_code == 404
