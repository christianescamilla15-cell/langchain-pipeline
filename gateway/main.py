"""API Gateway - Unified entry point routing to all microservices."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from services.document_service.main import app as doc_app, store as doc_store
from services.analysis_service.main import app as analysis_app, metrics as analysis_metrics
from services.report_service.main import app as report_app
from services.event_bus import EventBus
from services.mlops import PromptRegistry, MetricsTracker, StructuredLogger

app = FastAPI(
    title="LangChain Pipeline - API Gateway",
    version="1.0.0",
    description="Event-driven microservices with LangChain orchestration and MLOps",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount microservices
app.mount("/api/documents-service", doc_app)
app.mount("/api/analysis-service", analysis_app)
app.mount("/api/reports-service", report_app)

# Shared instances
prompt_registry = PromptRegistry()
logger = StructuredLogger()

# Register default prompts
prompt_registry.register(
    "extract_analysis",
    "Analyze this document and provide a structured analysis:\n\n{document}",
    "1.0.0",
)
prompt_registry.register(
    "quality_review",
    "Review this analysis:\n{analysis}\n\nRate quality 1-10.",
    "1.0.0",
)
prompt_registry.register(
    "quick_summary",
    "Summarize this document in 3 sentences:\n\n{document}",
    "1.0.0",
)

logger.info("gateway", "API Gateway started")


# --- Unified API routes ---

@app.get("/api/health")
async def health():
    bus = EventBus()
    return {
        "status": "healthy",
        "services": {
            "document_service": "running",
            "analysis_service": "running",
            "report_service": "running",
            "event_bus": "running",
        },
        "documents_count": doc_store.count(),
        "events_count": len(bus.get_log(limit=9999)),
    }


@app.get("/api/events")
async def get_events(limit: int = 50):
    bus = EventBus()
    return {"events": bus.get_log(limit=limit)}


@app.get("/api/mlops/metrics")
async def get_mlops_metrics():
    return {
        "dashboard": analysis_metrics.get_dashboard(),
        "all_names": analysis_metrics.get_all_names(),
    }


@app.get("/api/mlops/metrics/{name}")
async def get_metric_detail(name: str):
    return {
        "name": name,
        "summary": analysis_metrics.get_summary(name),
        "recent": analysis_metrics.get_metrics(name, limit=20),
    }


@app.get("/api/mlops/prompts")
async def get_prompts():
    names = prompt_registry.list_all_prompts()
    prompts = {}
    for name in names:
        prompts[name] = prompt_registry.list_versions(name)
    return {"prompts": prompts}


@app.get("/api/mlops/prompts/{name}")
async def get_prompt(name: str):
    active = prompt_registry.get_active(name)
    if not active:
        return {"error": "Prompt not found"}
    return {
        "name": name,
        "active_version": active.version,
        "template": active.template,
        "versions": prompt_registry.list_versions(name),
    }


@app.get("/api/mlops/logs")
async def get_logs(service: str = None, level: str = None, limit: int = 100):
    return {"logs": logger.get_logs(service=service, level=level, limit=limit)}


# Serve frontend static files if built
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
