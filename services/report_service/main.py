"""Report Service - FastAPI app for report generation and retrieval."""
from fastapi import FastAPI, HTTPException

from .generator import ReportGenerator
from .events import subscribe_to_analysis

app = FastAPI(title="Report Service", version="1.0.0")
generator = ReportGenerator()
_reports: dict[str, dict] = {}


@app.get("/reports")
async def list_reports():
    return {"reports": list(_reports.values()), "count": len(_reports)}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    report = _reports.get(report_id)
    if not report:
        # Try by document_id
        for r in _reports.values():
            if r.get("document_id") == report_id:
                return r
        raise HTTPException(status_code=404, detail="Report not found")
    return report


async def _handle_analysis_completed(event):
    """Auto-generate report when analysis completes."""
    payload = event.payload
    doc_id = payload.get("document_id", "unknown")
    analysis = payload.get("analysis", {})

    report = generator.generate(doc_id, analysis)
    _reports[report["report_id"]] = report


# Subscribe to events
subscribe_to_analysis(_handle_analysis_completed)
