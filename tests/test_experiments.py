"""Tests for A/B experiment management."""
import pytest

from services.mlops.experiments import ExperimentManager, get_experiment_manager


class TestExperimentManager:
    def test_create_experiment(self):
        mgr = ExperimentManager()
        exp = mgr.create("test_exp", "prompt_a", "v1.0", "v2.0")
        assert exp.name == "test_exp"
        assert exp.status == "running"
        assert exp.control.version == "v1.0"
        assert exp.treatment.version == "v2.0"

    def test_get_variant_deterministic(self):
        mgr = ExperimentManager()
        mgr.create("det_test", "prompt", "ctrl", "treat", split=0.5)

        # Same doc_id should always get same variant
        v1 = mgr.get_variant("det_test", "doc-123")
        v2 = mgr.get_variant("det_test", "doc-123")
        assert v1 == v2

    def test_get_variant_returns_none_for_concluded(self):
        mgr = ExperimentManager()
        mgr.create("done_test", "prompt", "ctrl", "treat")
        mgr.conclude("done_test")
        assert mgr.get_variant("done_test", "doc-1") is None

    def test_get_variant_returns_none_for_nonexistent(self):
        mgr = ExperimentManager()
        assert mgr.get_variant("nope", "doc-1") is None

    def test_record_results(self):
        mgr = ExperimentManager()
        mgr.create("rec_test", "prompt", "v1", "v2")

        mgr.record_result("rec_test", "v1", 7.5)
        mgr.record_result("rec_test", "v1", 8.0)
        mgr.record_result("rec_test", "v2", 9.0)

        results = mgr.get_results("rec_test")
        assert results["control"]["n"] == 2
        assert results["control"]["mean"] == pytest.approx(7.75)
        assert results["treatment"]["n"] == 1
        assert results["treatment"]["mean"] == 9.0

    def test_p_value_calculated_with_enough_data(self):
        mgr = ExperimentManager()
        mgr.create("pval_test", "prompt", "v1", "v2")

        for _ in range(20):
            mgr.record_result("pval_test", "v1", 7.0)
            mgr.record_result("pval_test", "v2", 9.0)

        results = mgr.get_results("pval_test")
        assert results["p_value"] is not None
        assert results["p_value"] < 0.05
        assert results["significant"] is True

    def test_p_value_none_with_insufficient_data(self):
        mgr = ExperimentManager()
        mgr.create("few_test", "prompt", "v1", "v2")
        mgr.record_result("few_test", "v1", 7.0)
        # Only 1 sample in control, 0 in treatment

        results = mgr.get_results("few_test")
        assert results["p_value"] is None
        assert results["significant"] is False

    def test_conclude_picks_winner(self):
        mgr = ExperimentManager()
        mgr.create("win_test", "prompt", "v1", "v2")

        for _ in range(10):
            mgr.record_result("win_test", "v1", 6.0)
            mgr.record_result("win_test", "v2", 9.0)

        winner = mgr.conclude("win_test")
        assert winner == "v2"

        results = mgr.get_results("win_test")
        assert results["status"] == "concluded"
        assert results["winner"] == "v2"

    def test_conclude_control_wins(self):
        mgr = ExperimentManager()
        mgr.create("ctrl_win", "prompt", "v1", "v2")

        for _ in range(10):
            mgr.record_result("ctrl_win", "v1", 9.0)
            mgr.record_result("ctrl_win", "v2", 6.0)

        winner = mgr.conclude("ctrl_win")
        assert winner == "v1"

    def test_conclude_nonexistent(self):
        mgr = ExperimentManager()
        assert mgr.conclude("nope") is None

    def test_list_experiments(self):
        mgr = ExperimentManager()
        mgr.create("exp_a", "prompt", "v1", "v2")
        mgr.create("exp_b", "prompt", "v1", "v2")

        exps = mgr.list_experiments()
        assert len(exps) == 2
        names = [e["name"] for e in exps]
        assert "exp_a" in names
        assert "exp_b" in names

    def test_get_results_nonexistent(self):
        mgr = ExperimentManager()
        assert mgr.get_results("nope") is None

    def test_variant_distribution(self):
        """Test that variant assignment distributes across both groups."""
        mgr = ExperimentManager()
        mgr.create("dist_test", "prompt", "ctrl", "treat", split=0.5)

        control_count = 0
        treatment_count = 0
        for i in range(100):
            v = mgr.get_variant("dist_test", f"doc-{i}")
            if v == "ctrl":
                control_count += 1
            else:
                treatment_count += 1

        # With 100 docs and 50/50 split, each group should have at least some
        assert control_count > 10
        assert treatment_count > 10

    def test_custom_split(self):
        mgr = ExperimentManager()
        exp = mgr.create("split_test", "prompt", "v1", "v2", split=0.9)
        assert exp.traffic_split == 0.9

    def test_record_result_nonexistent_experiment(self):
        mgr = ExperimentManager()
        # Should not raise
        mgr.record_result("nonexistent", "v1", 5.0)


class TestGetExperimentManager:
    def setup_method(self):
        import services.mlops.experiments as mod
        mod._manager = None

    def test_singleton(self):
        a = get_experiment_manager()
        b = get_experiment_manager()
        assert a is b
