"""LLM call observability — tracks tokens, latency, cost per chain step."""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# Pricing per 1M tokens (approximate)
MODEL_PRICING = {
    "mock-bedrock": {"input": 0.0, "output": 0.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "default": {"input": 3.0, "output": 15.0},
}


@dataclass
class LLMCallRecord:
    model: str
    chain_step: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float
    timestamp: str
    success: bool = True


class ObservabilityHandler(BaseCallbackHandler):
    """Callback handler that records token usage, latency, and cost for every LLM call."""

    def __init__(self, chain_step: str = "unknown"):
        self.chain_step = chain_step
        self._start_time: Optional[float] = None
        self._records: list[LLMCallRecord] = []
        self._model_name = "unknown"

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        self._start_time = time.time()
        self._model_name = serialized.get(
            "name",
            serialized.get("id", ["unknown"])[-1]
            if isinstance(serialized.get("id"), list)
            else "unknown",
        )

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        latency = int((time.time() - (self._start_time or time.time())) * 1000)

        # Extract token usage
        input_tokens = 0
        output_tokens = 0
        if response.llm_output and isinstance(response.llm_output, dict):
            usage = response.llm_output.get(
                "usage", response.llm_output.get("token_usage", {})
            )
            if isinstance(usage, dict):
                input_tokens = usage.get(
                    "input_tokens", usage.get("prompt_tokens", 0)
                )
                output_tokens = usage.get(
                    "output_tokens", usage.get("completion_tokens", 0)
                )

        # Estimate tokens from text if not available
        if input_tokens == 0 and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    output_tokens += len(gen.text.split()) * 1.3  # rough estimate
            input_tokens = output_tokens * 2  # rough input estimate

        input_tokens = int(input_tokens)
        output_tokens = int(output_tokens)

        # Calculate cost
        pricing = MODEL_PRICING.get(self._model_name, MODEL_PRICING["default"])
        cost = (
            input_tokens * pricing["input"] + output_tokens * pricing["output"]
        ) / 1_000_000

        record = LLMCallRecord(
            model=self._model_name,
            chain_step=self.chain_step,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            cost_usd=round(cost, 6),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._records.append(record)

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        latency = int((time.time() - (self._start_time or time.time())) * 1000)
        self._records.append(
            LLMCallRecord(
                model=self._model_name,
                chain_step=self.chain_step,
                input_tokens=0,
                output_tokens=0,
                latency_ms=latency,
                cost_usd=0.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                success=False,
            )
        )

    @property
    def records(self) -> list[dict]:
        return [
            {
                "model": r.model,
                "step": r.chain_step,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "latency_ms": r.latency_ms,
                "cost_usd": r.cost_usd,
                "timestamp": r.timestamp,
                "success": r.success,
            }
            for r in self._records
        ]


class GlobalObservability:
    """Singleton that aggregates all LLM call records across the application."""

    _instance: Optional["GlobalObservability"] = None

    def __new__(cls) -> "GlobalObservability":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._all_records: list[dict] = []
        return cls._instance

    def add_records(self, records: list[dict]) -> None:
        self._all_records.extend(records)

    def get_summary(self) -> dict:
        if not self._all_records:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "avg_latency_ms": 0,
                "models": {},
            }

        total_input = sum(r.get("input_tokens", 0) for r in self._all_records)
        total_output = sum(r.get("output_tokens", 0) for r in self._all_records)
        total_cost = sum(r.get("cost_usd", 0) for r in self._all_records)
        avg_latency = sum(r.get("latency_ms", 0) for r in self._all_records) / len(
            self._all_records
        )

        models = {}
        for r in self._all_records:
            m = r.get("model", "unknown")
            if m not in models:
                models[m] = {"calls": 0, "tokens": 0, "cost": 0, "errors": 0}
            models[m]["calls"] += 1
            models[m]["tokens"] += r.get("input_tokens", 0) + r.get(
                "output_tokens", 0
            )
            models[m]["cost"] += r.get("cost_usd", 0)
            if not r.get("success", True):
                models[m]["errors"] += 1

        return {
            "total_calls": len(self._all_records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 4),
            "avg_latency_ms": round(avg_latency),
            "models": models,
            "recent": self._all_records[-10:],
        }

    def get_records(self, limit: int = 50) -> list[dict]:
        return self._all_records[-limit:]

    def clear(self) -> None:
        self._all_records.clear()
