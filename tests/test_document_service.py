"""Tests for the document service."""
import pytest
from httpx import AsyncClient, ASGITransport
from services.document_service.main import app, store
from services.event_bus import EventBus


@pytest.fixture(autouse=True)
def clear_store():
    store._documents.clear()
    yield
    store._documents.clear()


@pytest.mark.asyncio
async def test_create_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/documents", json={
            "title": "Test Doc",
            "content": "This is a test document with enough content.",
            "doc_type": "general",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["document"]["title"] == "Test Doc"
        assert "id" in data["document"]


@pytest.mark.asyncio
async def test_list_documents():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/documents", json={
            "title": "Doc 1",
            "content": "Content for document one here.",
            "doc_type": "general",
        })
        resp = await client.get("/documents")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_get_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/documents", json={
            "title": "Get Test",
            "content": "Content for the get test document.",
            "doc_type": "contract",
        })
        doc_id = create_resp.json()["document"]["id"]

        resp = await client.get(f"/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.json()["document"]["title"] == "Get Test"


@pytest.mark.asyncio
async def test_get_document_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/documents/nonexistent-id")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/documents", json={
            "title": "Update Me",
            "content": "Original content that is long enough.",
            "doc_type": "general",
        })
        doc_id = create_resp.json()["document"]["id"]

        resp = await client.put(f"/documents/{doc_id}", json={
            "title": "Updated Title",
        })
        assert resp.status_code == 200
        assert resp.json()["document"]["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/documents", json={
            "title": "Delete Me",
            "content": "Content to be deleted from the store.",
            "doc_type": "general",
        })
        doc_id = create_resp.json()["document"]["id"]

        resp = await client.delete(f"/documents/{doc_id}")
        assert resp.status_code == 200

        get_resp = await client.get(f"/documents/{doc_id}")
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_doc_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/documents", json={
            "title": "Bad Type",
            "content": "This document has an invalid type.",
            "doc_type": "invalid_type",
        })
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_publishes_event():
    bus = EventBus()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/documents", json={
            "title": "Event Test",
            "content": "This tests that events are published.",
            "doc_type": "general",
        })

    log = bus.get_log()
    topics = [e["topic"] for e in log]
    assert "document.created" in topics
