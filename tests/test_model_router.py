"""Tests for ModelRouter and multi-model routing."""
from services.analysis_service.bedrock_client import ModelRouter, MockBedrockLLM, get_model_router


class TestModelRouter:
    def test_default_returns_mock(self):
        router = ModelRouter()
        llm, name = router.get_llm()
        assert isinstance(llm, MockBedrockLLM)
        assert name == "mock-bedrock"

    def test_record_call_success(self):
        router = ModelRouter()
        router.record_call("mock-bedrock", 100, True)
        status = router.get_model_status()
        mock = next(s for s in status if s["name"] == "mock-bedrock")
        assert mock["calls"] == 1

    def test_record_call_errors_degrade(self):
        router = ModelRouter()
        for _ in range(3):
            router.record_call("mock-bedrock", 100, False)
        status = router.get_model_status()
        mock = next(s for s in status if s["name"] == "mock-bedrock")
        assert mock["status"] == "degraded"

    def test_get_model_status_format(self):
        router = ModelRouter()
        status = router.get_model_status()
        assert len(status) >= 1
        assert "name" in status[0]
        assert "tier" in status[0]
        assert "avg_latency_ms" in status[0]

    def test_singleton_get_model_router(self):
        router1 = get_model_router()
        router2 = get_model_router()
        assert router1 is router2

    def test_record_call_tracks_latency(self):
        router = ModelRouter()
        router.record_call("mock-bedrock", 200, True)
        router.record_call("mock-bedrock", 400, True)
        status = router.get_model_status()
        mock = next(s for s in status if s["name"] == "mock-bedrock")
        assert mock["avg_latency_ms"] == 300
        assert mock["calls"] == 2

    def test_healthy_status_under_threshold(self):
        router = ModelRouter()
        router.record_call("mock-bedrock", 100, False)
        router.record_call("mock-bedrock", 100, False)
        status = router.get_model_status()
        mock = next(s for s in status if s["name"] == "mock-bedrock")
        # 2 errors is not enough to degrade (threshold is 3)
        assert mock["status"] == "healthy"

    def test_unknown_model_ignored(self):
        router = ModelRouter()
        # Should not raise
        router.record_call("nonexistent-model", 100, True)
