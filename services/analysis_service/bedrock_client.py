"""AWS Bedrock client with mock fallback and multi-model routing."""
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from typing import Any, Optional
import json
import re

from config import get_settings


class MockBedrockLLM(BaseChatModel):
    """Mock LLM that simulates Bedrock Claude responses for demo mode.
    Used when no AWS credentials or Anthropic API key is available."""

    model_name: str = "mock-bedrock-claude"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        **kwargs,
    ) -> ChatResult:
        last_msg = messages[-1].content if messages else ""

        # Detect what kind of response is needed
        all_text = str(messages)
        if "quality" in last_msg.lower() or "review" in last_msg.lower() or "Rate quality" in all_text:
            response = json.dumps(
                {
                    "score": 8,
                    "improvements": [
                        "Add more specific metrics",
                        "Include timeline estimates",
                    ],
                }
            )
        elif "JSON" in all_text or "json" in last_msg.lower():
            response = self._generate_json_response(last_msg)
        elif "summarize" in last_msg.lower() or "summary" in last_msg.lower():
            response = self._generate_summary(last_msg)
        elif "report" in last_msg.lower():
            response = self._generate_report(last_msg)
        else:
            response = (
                "Analysis complete. The document has been processed successfully."
            )

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=response))]
        )

    def _generate_json_response(self, text: str) -> str:
        words = text.split()
        word_count = len(words)
        has_risk = any(
            w in text.lower()
            for w in ["liability", "breach", "penalty", "risk"]
        )
        sentiment = "negative" if has_risk else "positive"
        risk = "high" if has_risk else "low"

        stop = {
            "the", "a", "an", "is", "are", "was", "were", "this", "that",
            "and", "or", "for", "to", "of", "in", "on", "with",
        }
        kw = [
            w.lower()
            for w in re.findall(r"\b[A-Za-z]{4,}\b", text)
            if w.lower() not in stop
        ]
        from collections import Counter

        top_kw = [w for w, _ in Counter(kw).most_common(5)]

        return json.dumps(
            {
                "summary": f"Document contains {word_count} words. "
                f"{'Risk factors detected.' if has_risk else 'No significant risks found.'} "
                f"Overall tone is {sentiment}.",
                "key_topics": top_kw[:5]
                if top_kw
                else ["general", "document", "analysis", "content", "review"],
                "sentiment": sentiment,
                "risk_level": risk,
                "action_items": [
                    "Review document for compliance requirements",
                    "Schedule follow-up review in 30 days",
                    "Share findings with stakeholders",
                ],
            }
        )

    def _generate_summary(self, text: str) -> str:
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 20
        ]
        if len(sentences) >= 3:
            return ". ".join(sentences[:3]) + "."
        return (
            "The document has been analyzed. "
            "Key information has been extracted. "
            "Recommendations are provided below."
        )

    def _generate_report(self, text: str) -> str:
        return json.dumps(
            {
                "title": "Document Analysis Report",
                "executive_summary": "The document has been thoroughly analyzed by the AI pipeline.",
                "findings": [
                    "Document structure is well-organized",
                    "Key terms and entities identified",
                    "Risk assessment completed",
                ],
                "recommendations": [
                    "Review flagged items with legal team",
                    "Implement suggested improvements",
                    "Schedule periodic re-analysis",
                ],
                "risk_assessment": "Moderate - standard business document with typical provisions",
            }
        )

    async def _agenerate(self, messages, stop=None, **kwargs):
        return self._generate(messages, stop, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "mock-bedrock"


class ModelRouter:
    """Routes LLM requests through a fallback chain of models."""

    def __init__(self):
        self._models = []
        self._stats = {}
        self._setup_models()

    def _setup_models(self):
        """Set up the model fallback chain."""
        settings = get_settings()
        api_key = settings.anthropic_api_key
        aws_region = settings.aws_default_region

        # Try Bedrock Sonnet (primary)
        if aws_region:
            try:
                from langchain_aws import ChatBedrock

                self._models.append({
                    "name": "bedrock-sonnet",
                    "llm": ChatBedrock(
                        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                        region_name=aws_region,
                    ),
                    "tier": "primary",
                })
            except Exception:
                pass

        # Try Bedrock Haiku (fallback 1)
        if aws_region:
            try:
                from langchain_aws import ChatBedrock

                self._models.append({
                    "name": "bedrock-haiku",
                    "llm": ChatBedrock(
                        model_id="anthropic.claude-3-haiku-20240307-v1:0",
                        region_name=aws_region,
                    ),
                    "tier": "fallback-1",
                })
            except Exception:
                pass

        # Try Anthropic API (fallback 2)
        if api_key:
            try:
                from langchain_anthropic import ChatAnthropic

                self._models.append({
                    "name": "anthropic-sonnet",
                    "llm": ChatAnthropic(
                        model="claude-sonnet-4-20250514",
                        api_key=api_key,
                        max_tokens=2000,
                    ),
                    "tier": "fallback-2",
                })
            except Exception:
                pass

        # Mock (always available)
        self._models.append({
            "name": "mock-bedrock",
            "llm": MockBedrockLLM(),
            "tier": "demo",
        })

        # Init stats
        for m in self._models:
            self._stats[m["name"]] = {
                "calls": 0,
                "errors": 0,
                "consecutive_errors": 0,
                "total_latency_ms": 0,
                "status": "healthy",
            }

    def get_llm(self, mode: str = "full"):
        """Get the best available LLM based on mode and health."""
        for model in self._models:
            if self._stats[model["name"]]["status"] != "unavailable":
                return model["llm"], model["name"]
        # Ultimate fallback
        return MockBedrockLLM(), "mock-bedrock"

    def record_call(self, model_name: str, latency_ms: int, success: bool):
        if model_name in self._stats:
            self._stats[model_name]["calls"] += 1
            self._stats[model_name]["total_latency_ms"] += latency_ms
            if success:
                self._stats[model_name]["consecutive_errors"] = 0
                if self._stats[model_name]["status"] == "degraded":
                    self._stats[model_name]["status"] = "healthy"
            else:
                self._stats[model_name]["errors"] += 1
                self._stats[model_name]["consecutive_errors"] = self._stats[model_name].get("consecutive_errors", 0) + 1
                if self._stats[model_name]["consecutive_errors"] >= 3:
                    self._stats[model_name]["status"] = "degraded"

    def get_model_status(self) -> list[dict]:
        result = []
        for m in self._models:
            name = m["name"]
            stats = self._stats[name]
            avg_latency = stats["total_latency_ms"] / max(stats["calls"], 1)
            result.append({
                "name": name,
                "tier": m["tier"],
                "status": stats["status"],
                "calls": stats["calls"],
                "errors": stats["errors"],
                "avg_latency_ms": round(avg_latency),
            })
        return result


# Singleton
_router = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def get_llm():
    """Get the best available LLM — backward compatible."""
    router = get_model_router()
    llm, _ = router.get_llm()
    return llm
