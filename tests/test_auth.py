"""Tests for API key authentication middleware."""
import pytest
from httpx import AsyncClient, ASGITransport
import os


@pytest.fixture
async def client():
    # Force non-demo mode for auth testing
    os.environ["PIPELINE_API_KEY"] = "test-secret-key"
    from gateway.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    os.environ.pop("PIPELINE_API_KEY", None)


@pytest.fixture
async def demo_client():
    # Demo mode — no auth required
    os.environ["PIPELINE_API_KEY"] = "demo"
    from gateway.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    os.environ.pop("PIPELINE_API_KEY", None)


class TestAPIKeyAuth:
    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client):
        r = await client.get("/api/health")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_protected_endpoint_no_key(self, client):
        r = await client.get("/api/events")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_valid_key(self, client):
        r = await client.get("/api/events", headers={"X-API-Key": "test-secret-key"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_protected_endpoint_invalid_key(self, client):
        r = await client.get("/api/events", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_401_response_body(self, client):
        r = await client.get("/api/events")
        assert r.json()["detail"] == "Invalid API key"


class TestDemoMode:
    @pytest.mark.asyncio
    async def test_demo_mode_no_auth_needed(self, demo_client):
        r = await demo_client.get("/api/events")
        assert r.status_code == 200
