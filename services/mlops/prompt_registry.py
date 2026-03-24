"""Versioned prompt management for LLMOps."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PromptVersion:
    template: str
    version: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict = field(default_factory=dict)
    is_active: bool = True


class PromptRegistry:
    """Registry for managing versioned prompts with A/B testing support."""

    def __init__(self):
        self._prompts: dict[str, list[PromptVersion]] = {}

    def register(self, name: str, template: str, version: str) -> PromptVersion:
        pv = PromptVersion(template=template, version=version)
        if name not in self._prompts:
            self._prompts[name] = []
        # Deactivate previous versions
        for p in self._prompts[name]:
            p.is_active = False
        self._prompts[name].append(pv)
        return pv

    def get_active(self, name: str) -> Optional[PromptVersion]:
        versions = self._prompts.get(name, [])
        for v in reversed(versions):
            if v.is_active:
                return v
        return None

    def get_version(self, name: str, version: str) -> Optional[PromptVersion]:
        for v in self._prompts.get(name, []):
            if v.version == version:
                return v
        return None

    def list_versions(self, name: str) -> list[dict]:
        return [
            {
                "version": v.version,
                "active": v.is_active,
                "created": v.created_at,
                "metrics": v.metrics,
            }
            for v in self._prompts.get(name, [])
        ]

    def record_metrics(self, name: str, version: str, metrics: dict):
        v = self.get_version(name, version)
        if v:
            v.metrics.update(metrics)

    def list_all_prompts(self) -> list[str]:
        return list(self._prompts.keys())
