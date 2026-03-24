"""Tests for LLM observability callbacks."""
import pytest
from langchain_core.outputs import LLMResult, Generation

from services.analysis_service.callbacks import (
    ObservabilityHandler,
    GlobalObservability,
    LLMCallRecord,
    MODEL_PRICING,
)


class TestObservabilityHandler:
    def test_records_llm_call(self):
        handler = ObservabilityHandler(chain_step="extraction")
        handler.on_llm_start({"name": "mock-bedrock"}, ["test prompt"])
        handler.on_llm_end(LLMResult(generations=[[Generation(text="hello world response")]]))

        records = handler.records
        assert len(records) == 1
        assert records[0]["step"] == "extraction"
        assert records[0]["model"] == "mock-bedrock"
        assert records[0]["success"] is True
        assert records[0]["latency_ms"] >= 0

    def test_records_error(self):
        handler = ObservabilityHandler(chain_step="quality_review")
        handler.on_llm_start({"name": "test-model"}, ["prompt"])
        handler.on_llm_error(Exception("timeout"))

        records = handler.records
        assert len(records) == 1
        assert records[0]["success"] is False
        assert records[0]["input_tokens"] == 0
        assert records[0]["output_tokens"] == 0

    def test_extracts_token_usage_from_llm_output(self):
        handler = ObservabilityHandler(chain_step="report")
        handler.on_llm_start({"name": "claude-3-sonnet"}, ["prompt"])
        result = LLMResult(
            generations=[[Generation(text="response")]],
            llm_output={"usage": {"input_tokens": 100, "output_tokens": 50}},
        )
        handler.on_llm_end(result)

        records = handler.records
        assert records[0]["input_tokens"] == 100
        assert records[0]["output_tokens"] == 50

    def test_calculates_cost(self):
        handler = ObservabilityHandler(chain_step="extraction")
        handler.on_llm_start({"name": "claude-3-sonnet"}, ["prompt"])
        result = LLMResult(
            generations=[[Generation(text="response")]],
            llm_output={"usage": {"input_tokens": 1000, "output_tokens": 500}},
        )
        handler.on_llm_end(result)

        records = handler.records
        # 1000 * 3.0 / 1M + 500 * 15.0 / 1M = 0.003 + 0.0075 = 0.0105
        assert records[0]["cost_usd"] == pytest.approx(0.0105, abs=0.001)

    def test_mock_model_zero_cost(self):
        handler = ObservabilityHandler(chain_step="test")
        handler.on_llm_start({"name": "mock-bedrock"}, ["prompt"])
        result = LLMResult(
            generations=[[Generation(text="response")]],
            llm_output={"usage": {"input_tokens": 100, "output_tokens": 50}},
        )
        handler.on_llm_end(result)

        assert handler.records[0]["cost_usd"] == 0.0

    def test_estimates_tokens_when_not_provided(self):
        handler = ObservabilityHandler(chain_step="test")
        handler.on_llm_start({"name": "mock-bedrock"}, ["prompt"])
        result = LLMResult(generations=[[Generation(text="a b c d e f g h i j")]])
        handler.on_llm_end(result)

        assert handler.records[0]["output_tokens"] > 0

    def test_multiple_calls_tracked(self):
        handler = ObservabilityHandler(chain_step="multi")
        for _ in range(3):
            handler.on_llm_start({"name": "mock-bedrock"}, ["p"])
            handler.on_llm_end(LLMResult(generations=[[Generation(text="ok")]]))

        assert len(handler.records) == 3

    def test_model_name_from_id_list(self):
        handler = ObservabilityHandler(chain_step="test")
        handler.on_llm_start({"id": ["langchain", "llms", "my-model"]}, ["prompt"])
        handler.on_llm_end(LLMResult(generations=[[Generation(text="ok")]]))

        assert handler.records[0]["model"] == "my-model"


class TestGlobalObservability:
    def setup_method(self):
        GlobalObservability._instance = None

    def test_empty_summary(self):
        obs = GlobalObservability()
        summary = obs.get_summary()
        assert summary["total_calls"] == 0
        assert summary["total_tokens"] == 0
        assert summary["total_cost_usd"] == 0

    def test_add_and_summarize(self):
        obs = GlobalObservability()
        obs.add_records([
            {"model": "mock-bedrock", "step": "extraction", "input_tokens": 100,
             "output_tokens": 50, "latency_ms": 200, "cost_usd": 0.0, "success": True},
            {"model": "mock-bedrock", "step": "quality", "input_tokens": 80,
             "output_tokens": 40, "latency_ms": 150, "cost_usd": 0.0, "success": True},
        ])

        summary = obs.get_summary()
        assert summary["total_calls"] == 2
        assert summary["total_input_tokens"] == 180
        assert summary["total_output_tokens"] == 90
        assert summary["total_tokens"] == 270
        assert summary["avg_latency_ms"] == 175
        assert "mock-bedrock" in summary["models"]
        assert summary["models"]["mock-bedrock"]["calls"] == 2

    def test_tracks_errors(self):
        obs = GlobalObservability()
        obs.add_records([
            {"model": "test", "step": "s", "input_tokens": 0, "output_tokens": 0,
             "latency_ms": 100, "cost_usd": 0, "success": False},
        ])

        summary = obs.get_summary()
        assert summary["models"]["test"]["errors"] == 1

    def test_get_records_with_limit(self):
        obs = GlobalObservability()
        for i in range(10):
            obs.add_records([{"model": "m", "step": "s", "input_tokens": i,
                             "output_tokens": 0, "latency_ms": 0, "cost_usd": 0, "success": True}])

        records = obs.get_records(limit=3)
        assert len(records) == 3
        assert records[0]["input_tokens"] == 7  # last 3

    def test_clear(self):
        obs = GlobalObservability()
        obs.add_records([{"model": "m", "step": "s", "input_tokens": 0,
                         "output_tokens": 0, "latency_ms": 0, "cost_usd": 0, "success": True}])
        obs.clear()
        assert obs.get_summary()["total_calls"] == 0

    def test_singleton_behavior(self):
        GlobalObservability._instance = None
        a = GlobalObservability()
        b = GlobalObservability()
        assert a is b
        a.add_records([{"model": "m", "step": "s", "input_tokens": 10,
                       "output_tokens": 5, "latency_ms": 0, "cost_usd": 0, "success": True}])
        assert b.get_summary()["total_calls"] == 1
