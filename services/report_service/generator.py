"""Report generation from analysis results."""
from datetime import datetime, timezone
import json
import uuid


class ReportGenerator:
    """Generate formatted reports from analysis results."""

    def generate(self, document_id: str, analysis: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()

        # Extract info from analysis
        if "analysis" in analysis and isinstance(analysis["analysis"], dict):
            a = analysis["analysis"]
            summary = a.get("summary", "No summary available")
            topics = a.get("key_topics", [])
            sentiment = a.get("sentiment", "unknown")
            risk = a.get("risk_level", "unknown")
            actions = a.get("action_items", [])
        else:
            summary = "Auto-analysis completed"
            topics = []
            sentiment = analysis.get("sentiment", "unknown")
            risk = "unknown"
            actions = []

        # Tool results
        tools = analysis.get("tools", {})
        keywords = tools.get("keywords", "[]")
        risk_terms = tools.get("risk_terms", "No risk terms detected")

        report = {
            "report_id": f"rpt-{uuid.uuid4().hex[:12]}",
            "document_id": document_id,
            "generated_at": now,
            "title": f"Analysis Report - {document_id[:8]}",
            "executive_summary": summary,
            "sections": [
                {
                    "heading": "Key Topics",
                    "content": topics if topics else ["General document analysis"],
                },
                {
                    "heading": "Sentiment Analysis",
                    "content": sentiment,
                },
                {
                    "heading": "Risk Assessment",
                    "content": risk,
                    "details": risk_terms,
                },
                {
                    "heading": "Keywords",
                    "content": keywords,
                },
                {
                    "heading": "Recommended Actions",
                    "content": actions if actions else ["Review document periodically"],
                },
            ],
            "quality_score": analysis.get("quality_review", {}).get("score", "N/A")
            if isinstance(analysis.get("quality_review"), dict)
            else "N/A",
            "mode": analysis.get("mode", "auto"),
        }

        return report
