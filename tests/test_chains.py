"""Tests for LangChain chains with mock LLM."""
import pytest
import json
from services.analysis_service.chains import (
    create_analysis_chain,
    create_simple_chain,
    extract_prompt,
    quality_prompt,
)
from services.analysis_service.bedrock_client import MockBedrockLLM


@pytest.fixture
def mock_llm():
    return MockBedrockLLM()


class TestMockLLM:
    def test_json_response(self, mock_llm):
        from langchain_core.messages import HumanMessage
        result = mock_llm.invoke([HumanMessage(content="Analyze this document about liability and breach in JSON format")])
        data = json.loads(result.content)
        assert "summary" in data
        assert "key_topics" in data
        assert data["risk_level"] == "high"

    def test_summary_response(self, mock_llm):
        from langchain_core.messages import HumanMessage
        result = mock_llm.invoke([HumanMessage(content="Summarize this text")])
        assert len(result.content) > 0

    def test_report_response(self, mock_llm):
        from langchain_core.messages import HumanMessage
        result = mock_llm.invoke([HumanMessage(content="Generate a report")])
        data = json.loads(result.content)
        assert "title" in data
        assert "findings" in data

    def test_llm_type(self, mock_llm):
        assert mock_llm._llm_type == "mock-bedrock"


class TestChains:
    def test_extract_chain(self, mock_llm):
        extract_chain, _, _ = create_analysis_chain(mock_llm)
        result = extract_chain.invoke({"document": "Test document about compliance and audit procedures."})
        assert isinstance(result, dict)
        assert "summary" in result

    def test_simple_chain(self, mock_llm):
        chain = create_simple_chain(mock_llm)
        result = chain.invoke({"document": "This is a fairly long document about business growth and market expansion in Q4."})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_quality_chain(self, mock_llm):
        _, quality_chain, _ = create_analysis_chain(mock_llm)
        analysis = json.dumps({"summary": "test", "key_topics": ["a"]})
        result = quality_chain.invoke({"analysis": analysis})
        assert isinstance(result, dict)
        assert "score" in result
