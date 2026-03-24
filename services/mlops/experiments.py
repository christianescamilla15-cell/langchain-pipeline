"""Prompt A/B testing with statistical significance."""
import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ExperimentVariant:
    version: str
    scores: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.scores)

    @property
    def mean(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0


@dataclass
class Experiment:
    name: str
    prompt_name: str
    control: ExperimentVariant
    treatment: ExperimentVariant
    traffic_split: float = 0.5  # fraction going to treatment
    status: str = "running"  # running, concluded
    winner: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ExperimentManager:
    def __init__(self):
        self._experiments: dict[str, Experiment] = {}

    def create(
        self,
        name: str,
        prompt_name: str,
        control_version: str,
        treatment_version: str,
        split: float = 0.5,
    ) -> Experiment:
        exp = Experiment(
            name=name,
            prompt_name=prompt_name,
            control=ExperimentVariant(version=control_version),
            treatment=ExperimentVariant(version=treatment_version),
            traffic_split=split,
        )
        self._experiments[name] = exp
        return exp

    def get_variant(self, experiment_name: str, document_id: str) -> Optional[str]:
        """Deterministic variant assignment based on document ID hash."""
        exp = self._experiments.get(experiment_name)
        if not exp or exp.status != "running":
            return None
        hash_val = (
            int(hashlib.md5(document_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        )
        return (
            exp.treatment.version
            if hash_val < exp.traffic_split
            else exp.control.version
        )

    def record_result(self, experiment_name: str, version: str, score: float):
        exp = self._experiments.get(experiment_name)
        if not exp:
            return
        if version == exp.control.version:
            exp.control.scores.append(score)
        elif version == exp.treatment.version:
            exp.treatment.scores.append(score)

    def get_results(self, experiment_name: str) -> Optional[dict]:
        exp = self._experiments.get(experiment_name)
        if not exp:
            return None

        p_value = self._calculate_p_value(exp.control.scores, exp.treatment.scores)

        return {
            "name": exp.name,
            "status": exp.status,
            "control": {
                "version": exp.control.version,
                "n": exp.control.count,
                "mean": round(exp.control.mean, 3),
            },
            "treatment": {
                "version": exp.treatment.version,
                "n": exp.treatment.count,
                "mean": round(exp.treatment.mean, 3),
            },
            "p_value": round(p_value, 4) if p_value else None,
            "significant": p_value < 0.05 if p_value else False,
            "winner": exp.winner,
        }

    def conclude(self, experiment_name: str) -> Optional[str]:
        exp = self._experiments.get(experiment_name)
        if not exp:
            return None
        exp.status = "concluded"
        if exp.treatment.mean > exp.control.mean:
            exp.winner = exp.treatment.version
        else:
            exp.winner = exp.control.version
        return exp.winner

    def list_experiments(self) -> list[dict]:
        return [self.get_results(name) for name in self._experiments]

    @staticmethod
    def _calculate_p_value(a: list[float], b: list[float]) -> Optional[float]:
        """Two-sample t-test p-value (manual, no scipy needed)."""
        if len(a) < 2 or len(b) < 2:
            return None

        mean_a = sum(a) / len(a)
        mean_b = sum(b) / len(b)
        var_a = sum((x - mean_a) ** 2 for x in a) / (len(a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in b) / (len(b) - 1)

        se = (
            math.sqrt(var_a / len(a) + var_b / len(b))
            if (var_a + var_b) > 0
            else 1
        )
        t_stat = abs(mean_a - mean_b) / se if se > 0 else 0

        # Approximate p-value using normal distribution
        z = t_stat
        p = math.erfc(z / math.sqrt(2))
        return p


# Singleton
_manager = None


def get_experiment_manager() -> ExperimentManager:
    global _manager
    if _manager is None:
        _manager = ExperimentManager()
    return _manager
