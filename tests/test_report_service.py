"""Tests for the report service."""
import pytest
from httpx import AsyncClient, ASGITransport
from services.report_service.main import app, _reports
from services.report_service.generator import ReportGenerator


@pytest.fixture(autouse=True)
def clear_reports():
    _reports.clear()
    yield
    _reports.clear()


class TestReportGenerator:
    def test_generate_full_report(self):
        gen = ReportGenerator()
        analysis = {
            "analysis": {
                "summary": "Test summary",
                "key_topics": ["topic1", "topic2"],
                "sentiment": "positive",
                "risk_level": "low",
                "action_items": ["action1"],
            },
            "quality_review": {"score": 8},
            "tools": {
                "keywords": "[{'keyword': 'test', 'count': 5}]",
                "risk_terms": "No risk terms detected",
            },
            "mode": "full",
        }
        report = gen.generate("doc-123", analysis)
        assert report["document_id"] == "doc-123"
        assert report["report_id"].startswith("rpt-")
        assert len(report["sections"]) == 5
        assert report["quality_score"] == 8

    def test_generate_auto_report(self):
        gen = ReportGenerator()
        analysis = {
            "auto_analysis": True,
            "keywords": "[]",
            "sentiment": "neutral",
        }
        report = gen.generate("doc-456", analysis)
        assert report["document_id"] == "doc-456"
        assert report["mode"] == "auto"


@pytest.mark.asyncio
async def test_list_reports():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/reports")
        assert resp.status_code == 200
        assert "reports" in resp.json()


@pytest.mark.asyncio
async def test_get_report_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/reports/nonexistent")
        assert resp.status_code == 404
