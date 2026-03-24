"""Quality metrics tracking for LLMOps monitoring."""
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, stdev


@dataclass
class MetricEntry:
    name: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)


class MetricsTracker:
    """Track and analyze LLM quality metrics over time."""

    def __init__(self):
        self._metrics: list[MetricEntry] = []

    def record(self, name: str, value: float, metadata: dict = None):
        self._metrics.append(
            MetricEntry(name=name, value=value, metadata=metadata or {})
        )

    def get_metrics(self, name: str, limit: int = 100) -> list[dict]:
        filtered = [m for m in self._metrics if m.name == name][-limit:]
        return [
            {"value": m.value, "timestamp": m.timestamp, "metadata": m.metadata}
            for m in filtered
        ]

    def get_summary(self, name: str) -> dict:
        values = [m.value for m in self._metrics if m.name == name]
        if not values:
            return {"count": 0, "mean": 0, "min": 0, "max": 0, "stdev": 0}
        return {
            "count": len(values),
            "mean": round(mean(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "stdev": round(stdev(values), 3) if len(values) > 1 else 0,
        }

    def get_all_names(self) -> list[str]:
        return list(set(m.name for m in self._metrics))

    def get_dashboard(self) -> dict:
        names = self.get_all_names()
        return {name: self.get_summary(name) for name in names}
