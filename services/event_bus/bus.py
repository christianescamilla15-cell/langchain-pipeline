"""In-memory event bus simulating Redis pub/sub for microservice communication."""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Any
from collections import defaultdict
import json


@dataclass
class Event:
    topic: str
    payload: dict
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_id: str = field(default_factory=lambda: f"evt-{id(object()):x}")


class EventBus:
    """Singleton event bus for inter-service communication."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = defaultdict(list)
            cls._instance._event_log = []
        return cls._instance

    def subscribe(self, topic: str, handler: Callable):
        self._subscribers[topic].append(handler)

    async def publish(self, topic: str, payload: dict):
        event = Event(topic=topic, payload=payload)
        self._event_log.append(event)
        for handler in self._subscribers[topic]:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

    def get_log(self, limit: int = 50) -> list[dict]:
        return [
            {
                "topic": e.topic,
                "payload": e.payload,
                "timestamp": e.timestamp,
                "id": e.event_id,
            }
            for e in self._event_log[-limit:]
        ]

    def clear(self):
        self._subscribers.clear()
        self._event_log.clear()
        EventBus._instance = None
