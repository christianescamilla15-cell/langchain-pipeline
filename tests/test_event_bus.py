"""Tests for the event bus."""
import pytest
from services.event_bus import EventBus, Event


class TestEventBus:
    def test_singleton(self):
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe("test.topic", handler)
        await bus.publish("test.topic", {"key": "value"})

        assert len(received) == 1
        assert received[0].topic == "test.topic"
        assert received[0].payload == {"key": "value"}

    @pytest.mark.asyncio
    async def test_sync_handler(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("sync.topic", handler)
        await bus.publish("sync.topic", {"data": 42})

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_event_log(self):
        bus = EventBus()
        await bus.publish("topic.a", {"a": 1})
        await bus.publish("topic.b", {"b": 2})

        log = bus.get_log()
        assert len(log) == 2
        assert log[0]["topic"] == "topic.a"
        assert log[1]["topic"] == "topic.b"

    @pytest.mark.asyncio
    async def test_event_log_limit(self):
        bus = EventBus()
        for i in range(10):
            await bus.publish("topic", {"i": i})

        log = bus.get_log(limit=3)
        assert len(log) == 3

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = EventBus()
        results_a = []
        results_b = []

        async def handler_a(event):
            results_a.append(event)

        async def handler_b(event):
            results_b.append(event)

        bus.subscribe("multi", handler_a)
        bus.subscribe("multi", handler_b)
        await bus.publish("multi", {"msg": "hello"})

        assert len(results_a) == 1
        assert len(results_b) == 1

    def test_clear(self):
        bus = EventBus()
        bus.subscribe("x", lambda e: None)
        bus.clear()
        # After clear, singleton is reset
        bus2 = EventBus()
        assert bus2 is not bus

    @pytest.mark.asyncio
    async def test_event_has_id_and_timestamp(self):
        bus = EventBus()
        await bus.publish("meta", {"test": True})
        log = bus.get_log()
        assert "id" in log[0]
        assert "timestamp" in log[0]
        assert log[0]["id"].startswith("evt-")
