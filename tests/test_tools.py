"""Tests for LangChain analysis tools."""
import json
import pytest
from services.analysis_service.tools import extract_keywords, detect_risk_terms, analyze_sentiment_basic, count_sections


class TestExtractKeywords:
    def test_extracts_top_keywords(self):
        result = extract_keywords.invoke("python python python javascript javascript ruby")
        data = json.loads(result)
        assert len(data) > 0
        assert data[0]["keyword"] == "python"

    def test_empty_input(self):
        result = extract_keywords.invoke("")
        assert result is not None

    def test_all_stop_words(self):
        result = extract_keywords.invoke("the the the is are was")
        data = json.loads(result)
        assert len(data) == 0

    def test_counts_are_correct(self):
        result = extract_keywords.invoke("python python ruby ruby ruby java")
        data = json.loads(result)
        keywords = {d["keyword"]: d["count"] for d in data}
        assert keywords["ruby"] == 3
        assert keywords["python"] == 2
        assert keywords["java"] == 1

    def test_returns_json_string(self):
        result = extract_keywords.invoke("analysis document review compliance audit")
        data = json.loads(result)
        assert isinstance(data, list)
        for item in data:
            assert "keyword" in item
            assert "count" in item


class TestDetectRiskTerms:
    def test_finds_risk_terms(self):
        result = detect_risk_terms.invoke("This has liability and breach of contract with penalty")
        data = json.loads(result)
        assert len(data) >= 3

    def test_no_risks(self):
        result = detect_risk_terms.invoke("A beautiful sunny day in the park")
        assert "No risk terms" in result

    def test_finds_all_risk_categories(self):
        text = "liability breach penalty termination indemnification confidential deadline compliance audit default"
        result = detect_risk_terms.invoke(text)
        data = json.loads(result)
        assert len(data) >= 8

    def test_result_structure(self):
        result = detect_risk_terms.invoke("There is significant liability in this clause")
        data = json.loads(result)
        assert len(data) >= 1
        assert "term" in data[0]
        assert "flag" in data[0]


class TestAnalyzeSentiment:
    def test_positive(self):
        result = analyze_sentiment_basic.invoke("great success excellent growth positive")
        assert result == "positive"

    def test_negative(self):
        result = analyze_sentiment_basic.invoke("bad risk loss damage fail problem")
        assert result == "negative"

    def test_neutral(self):
        result = analyze_sentiment_basic.invoke("the document contains several paragraphs")
        assert result == "neutral"

    def test_mixed_defaults_to_neutral(self):
        result = analyze_sentiment_basic.invoke("good bad")
        assert result == "neutral"


class TestCountSections:
    def test_counts_correctly(self):
        result = count_sections.invoke("First paragraph.\n\nSecond paragraph. With two sentences.")
        data = json.loads(result)
        assert data["paragraphs"] >= 2
        assert data["words"] > 0

    def test_single_paragraph(self):
        result = count_sections.invoke("Just one paragraph with some words.")
        data = json.loads(result)
        assert data["paragraphs"] == 1
        assert data["words"] > 0

    def test_structure_keys(self):
        result = count_sections.invoke("Test document content here.")
        data = json.loads(result)
        assert "paragraphs" in data
        assert "sentences" in data
        assert "words" in data
