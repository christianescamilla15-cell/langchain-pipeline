"""Event handling for analysis service."""
from services.event_bus import EventBus


async def publish_analysis_completed(document_id: str, analysis: dict):
    bus = EventBus()
    await bus.publish("analysis.completed", {
        "document_id": document_id,
        "analysis": analysis,
    })


def subscribe_to_documents(handler):
    """Subscribe to document.created events."""
    bus = EventBus()
    bus.subscribe("document.created", handler)
