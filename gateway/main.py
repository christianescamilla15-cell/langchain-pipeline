"""API Gateway - Unified entry point routing to all microservices."""
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from services.document_service.main import app as doc_app, store as doc_store
from services.analysis_service.main import app as analysis_app, metrics as analysis_metrics, set_prompt_registry
from services.report_service.main import app as report_app
from services.analysis_service.rag import get_vector_store
from services.analysis_service.callbacks import GlobalObservability
from services.analysis_service.bedrock_client import get_model_router
from services.event_bus import EventBus
from services.mlops import PromptRegistry, MetricsTracker, StructuredLogger
from services.mlops.experiments import get_experiment_manager
from gateway.auth import APIKeyMiddleware

app = FastAPI(
    title="LangChain Pipeline - API Gateway",
    version="1.0.0",
    description="Event-driven microservices with LangChain orchestration and MLOps",
)

app.add_middleware(APIKeyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://langchain-pipeline.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
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

prompt_registry.register(
    "final_report",
    "Based on this analysis:\n{analysis}\n\nAnd quality review:\n{review}\n\nGenerate a final executive report with: title, executive_summary, findings (list), recommendations (list), risk_assessment.",
    "1.0.0",
)

# Wire prompt registry to analysis service
set_prompt_registry(prompt_registry)

# Seed demo metrics
import random
for i in range(10):
    analysis_metrics.record("analysis_quality", random.uniform(7.0, 9.5))
    analysis_metrics.record("analyses_completed", 1.0)
    analysis_metrics.record("processing_time_ms", random.uniform(800, 3500))
    analysis_metrics.record("input_tokens", random.uniform(500, 2000))
    analysis_metrics.record("output_tokens", random.uniform(200, 800))

# Seed demo experiment
exp_mgr = get_experiment_manager()
exp_mgr.create("extract_v2_test", "extract_analyze", "v1.0", "v2.0", 0.5)
for _ in range(15):
    exp_mgr.record_result("extract_v2_test", "v1.0", random.uniform(6.5, 8.5))
    exp_mgr.record_result("extract_v2_test", "v2.0", random.uniform(7.0, 9.5))

logger.info("gateway", "API Gateway started")


# --- Unified API routes ---

@app.get("/api/health")
async def health() -> dict[str, Any]:
    bus = EventBus()
    store = get_vector_store()
    return {
        "status": "healthy",
        "services": {
            "document_service": "running",
            "analysis_service": "running",
            "report_service": "running",
            "event_bus": "running",
            "rag_store": "running",
        },
        "documents_count": doc_store.count(),
        "events_count": len(bus.get_log(limit=9999)),
        "rag_chunks": store.chunk_count,
        "rag_documents": store.doc_count,
    }


@app.get("/api/events")
async def get_events(limit: int = 50) -> dict[str, Any]:
    bus = EventBus()
    return {"events": bus.get_log(limit=limit)}


@app.get("/api/rag/search")
async def rag_search(query: str, top_k: int = 3) -> dict[str, Any]:
    store = get_vector_store()
    return {"results": store.search(query, top_k), "total_chunks": store.chunk_count}


@app.get("/api/rag/stats")
async def rag_stats() -> dict[str, int]:
    store = get_vector_store()
    return {"chunks": store.chunk_count, "documents": store.doc_count}


@app.get("/api/mlops/metrics")
async def get_mlops_metrics() -> dict[str, Any]:
    return {
        "dashboard": analysis_metrics.get_dashboard(),
        "all_names": analysis_metrics.get_all_names(),
    }


@app.get("/api/mlops/metrics/{name}")
async def get_metric_detail(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "summary": analysis_metrics.get_summary(name),
        "recent": analysis_metrics.get_metrics(name, limit=20),
    }


@app.get("/api/mlops/prompts")
async def get_prompts() -> dict[str, Any]:
    names = prompt_registry.list_all_prompts()
    prompts = {}
    for name in names:
        prompts[name] = prompt_registry.list_versions(name)
    return {"prompts": prompts}


@app.get("/api/mlops/prompts/{name}")
async def get_prompt(name: str) -> dict[str, Any]:
    active = prompt_registry.get_active(name)
    if not active:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {
        "name": name,
        "active_version": active.version,
        "template": active.template,
        "versions": prompt_registry.list_versions(name),
    }


@app.get("/api/mlops/logs")
async def get_logs(service: Optional[str] = None, level: Optional[str] = None, limit: int = 100) -> dict[str, Any]:
    return {"logs": logger.get_logs(service=service, level=level, limit=limit)}


@app.get("/api/mlops/llm-costs")
async def llm_costs() -> dict[str, Any]:
    obs = GlobalObservability()
    return obs.get_summary()


@app.get("/api/mlops/models")
async def model_status() -> dict[str, Any]:
    router = get_model_router()
    return {"models": router.get_model_status()}


@app.get("/api/mlops/experiments")
async def list_experiments() -> dict[str, Any]:
    mgr = get_experiment_manager()
    return {"experiments": mgr.list_experiments()}


@app.post("/api/mlops/experiments")
async def create_experiment(body: dict) -> Optional[dict[str, Any]]:
    mgr = get_experiment_manager()
    mgr.create(body["name"], body["prompt_name"], body["control"], body["treatment"], body.get("split", 0.5))
    return mgr.get_results(body["name"])


@app.post("/api/mlops/experiments/{name}/conclude")
async def conclude_experiment(name: str) -> dict[str, Any]:
    mgr = get_experiment_manager()
    winner = mgr.conclude(name)
    if not winner:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"winner": winner, "results": mgr.get_results(name)}


# Serve frontend static files if built
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
