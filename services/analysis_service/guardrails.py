"""Input/output guardrails for LLM safety and quality."""
import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str]
    sanitized_content: str = ""


class InputGuardrails:
    """Pre-processing validation for document content before LLM analysis."""

    PII_PATTERNS: dict[str, str] = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "phone_mx": r"\b\+?52?\s?\d{2}\s?\d{4}\s?\d{4}\b",
    }

    @classmethod
    def validate(cls, content: str, max_length: int = 100000) -> ValidationResult:
        issues = []

        if len(content) > max_length:
            issues.append(
                f"Content exceeds maximum length ({len(content)} > {max_length})"
            )

        if len(content.split()) < 5:
            issues.append("Content too short for meaningful analysis")

        # PII detection (warn, don't block)
        pii_found = []
        for pii_type, pattern in cls.PII_PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                pii_found.append(f"{pii_type}: {len(matches)} instance(s)")

        if pii_found:
            issues.append(f"PII detected: {', '.join(pii_found)}")

        # Prompt injection detection
        injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions",
            r"disregard\s+(all\s+)?above",
            r"you\s+are\s+now\s+a",
            r"system\s*:\s*",
            r"<\s*/?system\s*>",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append("Potential prompt injection detected")
                break

        return ValidationResult(
            valid=len(
                [
                    i
                    for i in issues
                    if "PII" not in i and "injection" not in i.lower()
                ]
            )
            == 0,
            issues=issues,
            sanitized_content=content[:max_length],
        )


class OutputGuardrails:
    """Post-processing validation for LLM analysis output."""

    REQUIRED_FIELDS = {"summary", "key_topics", "sentiment", "risk_level", "action_items"}
    VALID_SENTIMENTS = {"positive", "negative", "neutral"}
    VALID_RISK_LEVELS = {"low", "medium", "high"}

    @classmethod
    def validate(cls, output: dict, original_content: str = "") -> ValidationResult:
        issues = []

        if not isinstance(output, dict):
            return ValidationResult(valid=False, issues=["Output is not a dictionary"])

        # Check required fields
        missing = cls.REQUIRED_FIELDS - set(output.keys())
        if missing:
            issues.append(f"Missing fields: {missing}")

        # Validate sentiment
        sentiment = output.get("sentiment", "")
        if sentiment and sentiment.lower() not in cls.VALID_SENTIMENTS:
            issues.append(
                f"Invalid sentiment: '{sentiment}' (expected: {cls.VALID_SENTIMENTS})"
            )

        # Validate risk level
        risk = output.get("risk_level", "")
        if risk and risk.lower() not in cls.VALID_RISK_LEVELS:
            issues.append(
                f"Invalid risk_level: '{risk}' (expected: {cls.VALID_RISK_LEVELS})"
            )

        # Check summary is not empty
        summary = output.get("summary", "")
        if isinstance(summary, str) and len(summary) < 10:
            issues.append("Summary too short")

        # Basic hallucination check — do key topics appear in the document?
        if original_content:
            topics = output.get("key_topics", [])
            if isinstance(topics, list):
                content_lower = original_content.lower()
                hallucinated = [
                    t
                    for t in topics
                    if isinstance(t, str) and t.lower() not in content_lower
                ]
                if len(hallucinated) > len(topics) * 0.5:
                    issues.append(
                        f"Possible hallucination: {len(hallucinated)}/{len(topics)} topics not found in document"
                    )

        return ValidationResult(valid=len(issues) == 0, issues=issues)
