"""Tests for MLOps components."""
import pytest
from services.mlops.prompt_registry import PromptRegistry
from services.mlops.metrics import MetricsTracker
from services.mlops.logger import StructuredLogger


class TestPromptRegistry:
    def test_register_and_get_active(self):
        reg = PromptRegistry()
        reg.register("test_prompt", "Hello {name}", "1.0.0")
        active = reg.get_active("test_prompt")
        assert active is not None
        assert active.version == "1.0.0"
        assert active.template == "Hello {name}"

    def test_new_version_deactivates_old(self):
        reg = PromptRegistry()
        reg.register("p", "v1 template", "1.0.0")
        reg.register("p", "v2 template", "2.0.0")

        active = reg.get_active("p")
        assert active.version == "2.0.0"

        versions = reg.list_versions("p")
        assert len(versions) == 2
        assert versions[0]["active"] is False
        assert versions[1]["active"] is True

    def test_get_specific_version(self):
        reg = PromptRegistry()
        reg.register("p", "template A", "1.0.0")
        reg.register("p", "template B", "2.0.0")

        v1 = reg.get_version("p", "1.0.0")
        assert v1.template == "template A"

    def test_record_metrics(self):
        reg = PromptRegistry()
        reg.register("p", "tmpl", "1.0.0")
        reg.record_metrics("p", "1.0.0", {"accuracy": 0.95})

        v = reg.get_version("p", "1.0.0")
        assert v.metrics["accuracy"] == 0.95

    def test_list_all_prompts(self):
        reg = PromptRegistry()
        reg.register("a", "tmpl_a", "1.0.0")
        reg.register("b", "tmpl_b", "1.0.0")
        assert set(reg.list_all_prompts()) == {"a", "b"}

    def test_get_active_nonexistent(self):
        reg = PromptRegistry()
        assert reg.get_active("nope") is None


class TestMetricsTracker:
    def test_record_and_get(self):
        mt = MetricsTracker()
        mt.record("latency", 0.5)
        mt.record("latency", 0.7)

        metrics = mt.get_metrics("latency")
        assert len(metrics) == 2
        assert metrics[0]["value"] == 0.5

    def test_summary(self):
        mt = MetricsTracker()
        mt.record("score", 8.0)
        mt.record("score", 9.0)
        mt.record("score", 7.0)

        summary = mt.get_summary("score")
        assert summary["count"] == 3
        assert summary["mean"] == 8.0
        assert summary["min"] == 7.0
        assert summary["max"] == 9.0

    def test_empty_summary(self):
        mt = MetricsTracker()
        summary = mt.get_summary("empty")
        assert summary["count"] == 0

    def test_dashboard(self):
        mt = MetricsTracker()
        mt.record("a", 1.0)
        mt.record("b", 2.0)

        dashboard = mt.get_dashboard()
        assert "a" in dashboard
        assert "b" in dashboard

    def test_get_all_names(self):
        mt = MetricsTracker()
        mt.record("x", 1.0)
        mt.record("y", 2.0)
        names = mt.get_all_names()
        assert set(names) == {"x", "y"}


class TestStructuredLogger:
    def test_log_levels(self):
        logger = StructuredLogger()
        logger.info("test_svc", "Info message")
        logger.warn("test_svc", "Warn message")
        logger.error("test_svc", "Error message")

        logs = logger.get_logs()
        assert len(logs) == 3
        levels = [l["level"] for l in logs]
        assert "INFO" in levels
        assert "WARN" in levels
        assert "ERROR" in levels

    def test_filter_by_service(self):
        logger = StructuredLogger()
        logger.info("svc_a", "msg a")
        logger.info("svc_b", "msg b")

        logs = logger.get_logs(service="svc_a")
        assert len(logs) == 1
        assert logs[0]["service"] == "svc_a"

    def test_filter_by_level(self):
        logger = StructuredLogger()
        logger.info("svc", "info")
        logger.error("svc", "error")

        logs = logger.get_logs(level="ERROR")
        assert len(logs) == 1
        assert logs[0]["level"] == "ERROR"

    def test_metadata(self):
        logger = StructuredLogger()
        logger.info("svc", "test", doc_id="123", score=9.5)

        logs = logger.get_logs()
        assert logs[0]["metadata"]["doc_id"] == "123"
        assert logs[0]["metadata"]["score"] == 9.5
