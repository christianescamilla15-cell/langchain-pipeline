"""Tests for the API gateway."""
import pytest
from httpx import AsyncClient, ASGITransport
from gateway.main import app


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert data["services"]["document_service"] == "running"


@pytest.mark.asyncio
async def test_events():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/events")
        assert resp.status_code == 200
        assert "events" in resp.json()


@pytest.mark.asyncio
async def test_mlops_metrics():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/mlops/metrics")
        assert resp.status_code == 200
        assert "dashboard" in resp.json()


@pytest.mark.asyncio
async def test_mlops_prompts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/mlops/prompts")
        assert resp.status_code == 200
        data = resp.json()
        assert "prompts" in data
        assert "extract_analysis" in data["prompts"]


@pytest.mark.asyncio
async def test_mlops_prompt_detail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/mlops/prompts/extract_analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_mlops_logs():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/mlops/logs")
        assert resp.status_code == 200
        assert "logs" in resp.json()
