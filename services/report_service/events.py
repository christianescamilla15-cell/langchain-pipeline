"""Event handling for report service."""
from services.event_bus import EventBus


def subscribe_to_analysis(handler):
    """Subscribe to analysis.completed events."""
    bus = EventBus()
    bus.subscribe("analysis.completed", handler)
