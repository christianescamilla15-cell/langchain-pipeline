"""LangChain tools for document processing."""
from langchain_core.tools import tool
import re
from collections import Counter


@tool
def extract_keywords(text: str) -> str:
    """Extract top keywords from document text using TF analysis."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "have",
        "has", "had", "do", "does", "did", "will", "would", "could", "should",
        "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
        "into", "through", "this", "that", "it", "and", "or", "but", "not",
        "no", "if", "so", "than", "too", "very", "can", "just", "its",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    filtered = [w for w in words if w not in stop_words]
    counts = Counter(filtered).most_common(10)
    return str([{"keyword": w, "count": c} for w, c in counts])


@tool
def detect_risk_terms(text: str) -> str:
    """Detect legal and financial risk terms in document."""
    risk_patterns = {
        "liability": "Legal liability language detected",
        "breach": "Contract breach terminology found",
        "penalty": "Penalty clauses identified",
        "termination": "Termination provisions present",
        "indemnif": "Indemnification clauses found",
        "confidential": "Confidentiality requirements",
        "deadline": "Time-sensitive deadlines",
        "compliance": "Compliance requirements noted",
        "audit": "Audit provisions found",
        "default": "Default conditions specified",
    }
    text_lower = text.lower()
    found = []
    for pattern, message in risk_patterns.items():
        if pattern in text_lower:
            found.append({"term": pattern, "flag": message})
    return str(found) if found else "No risk terms detected"


@tool
def analyze_sentiment_basic(text: str) -> str:
    """Perform basic sentiment analysis on document text."""
    pos = {
        "good", "great", "excellent", "positive", "success", "benefit",
        "improve", "growth", "profit", "strong", "favorable",
    }
    neg = {
        "bad", "poor", "negative", "risk", "loss", "damage", "fail",
        "decline", "problem", "issue", "concern", "liability",
    }
    words = set(text.lower().split())
    p = len(words & pos)
    n = len(words & neg)
    if p > n:
        return "positive"
    elif n > p:
        return "negative"
    return "neutral"


@tool
def count_sections(text: str) -> str:
    """Count document structure: paragraphs, sentences, words."""
    paragraphs = len([p for p in text.split("\n\n") if p.strip()])
    sentences = len(re.split(r"[.!?]+", text))
    words = len(text.split())
    return str({"paragraphs": paragraphs, "sentences": sentences, "words": words})


ANALYSIS_TOOLS = [extract_keywords, detect_risk_terms, analyze_sentiment_basic, count_sections]
