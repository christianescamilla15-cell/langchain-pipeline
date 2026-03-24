"""Event publishing for document service."""
from services.event_bus import EventBus


async def publish_document_created(doc: dict):
    bus = EventBus()
    await bus.publish("document.created", {
        "document_id": doc["id"],
        "title": doc["title"],
        "content": doc["content"],
        "doc_type": doc["doc_type"],
    })


async def publish_document_deleted(doc_id: str):
    bus = EventBus()
    await bus.publish("document.deleted", {"document_id": doc_id})
