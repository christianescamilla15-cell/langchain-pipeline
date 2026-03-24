"""Analysis Service - FastAPI app for LangChain document analysis."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import json

from .chains import create_analysis_chain, create_simple_chain, create_agent_chain, create_composed_chain
from .tools import extract_keywords, detect_risk_terms, analyze_sentiment_basic, count_sections, ANALYSIS_TOOLS
from .bedrock_client import get_llm
from .events import publish_analysis_completed, subscribe_to_documents
from .rag import get_vector_store
from services.mlops.metrics import MetricsTracker

app = FastAPI(title="Analysis Service", version="1.0.0")
metrics = MetricsTracker()
_analyses: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    document_id: str = Field(default="direct")
    content: str = Field(..., min_length=10)
    mode: str = Field(default="full", description="full or quick")


@app.post("/analyze")
async def analyze_document(body: AnalyzeRequest):
    llm = get_llm()

    # Run tools first
    keywords = extract_keywords.invoke(body.content)
    risk_terms = detect_risk_terms.invoke(body.content)
    sentiment = analyze_sentiment_basic.invoke(body.content)
    structure = count_sections.invoke(body.content)

    tool_results = {
        "keywords": keywords,
        "risk_terms": risk_terms,
        "sentiment": sentiment,
        "structure": structure,
    }

    if body.mode == "quick":
        chain = create_simple_chain(llm)
        summary = chain.invoke({"document": body.content})
        result = {
            "document_id": body.document_id,
            "summary": summary,
            "tools": tool_results,
            "mode": "quick",
        }
    else:
        # Try agent first, fallback to manual chains
        agent_executor = create_agent_chain(llm, ANALYSIS_TOOLS)
        agent_used = False

        if agent_executor:
            try:
                agent_result = agent_executor.invoke({"document": body.content})
                # Parse agent output
                agent_output = agent_result.get("output", "")
                try:
                    analysis = json.loads(agent_output)
                except (json.JSONDecodeError, TypeError):
                    analysis = {"summary": agent_output, "key_topics": [], "sentiment": "neutral", "risk_level": "low", "action_items": []}
                agent_used = True
            except Exception:
                agent_used = False

        if not agent_used:
            # Fallback to manual chains
            extract_chain, quality_chain, report_chain = create_analysis_chain(llm)

            # Step 1: Extract & analyze
            analysis = extract_chain.invoke({"document": body.content})

        # Step 2: Quality review (always run)
        _, quality_chain, report_chain = create_analysis_chain(llm)
        analysis_str = json.dumps(analysis) if isinstance(analysis, dict) else analysis
        quality = quality_chain.invoke({"analysis": analysis_str})

        # Step 3: Final report
        quality_str = json.dumps(quality)
        report = report_chain.invoke({"analysis": analysis_str, "review": quality_str})

        # Track metrics
        if isinstance(quality, dict) and "score" in quality:
            metrics.record("analysis_quality", float(quality["score"]),
                          metadata={"document_id": body.document_id})

        metrics.record("analyses_completed", 1.0,
                       metadata={"mode": body.mode})

        result = {
            "document_id": body.document_id,
            "analysis": analysis,
            "quality_review": quality,
            "report": report,
            "tools": tool_results,
            "mode": "full",
            "agent_used": agent_used,
        }

    # Add document to RAG vector store
    store = get_vector_store()
    chunks_added = store.add_document(body.document_id, body.content)
    result["rag_chunks_added"] = chunks_added

    _analyses[body.document_id] = result
    await publish_analysis_completed(body.document_id, result)
    return result


@app.get("/analyses")
async def list_analyses():
    return {"analyses": list(_analyses.values()), "count": len(_analyses)}


@app.get("/analyses/{doc_id}")
async def get_analysis(doc_id: str):
    if doc_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return _analyses[doc_id]


async def _handle_document_created(event):
    """Auto-analyze documents when created."""
    payload = event.payload
    llm = get_llm()
    content = payload.get("content", "")
    doc_id = payload.get("document_id", "unknown")

    # Run quick tools analysis
    keywords = extract_keywords.invoke(content)
    sentiment = analyze_sentiment_basic.invoke(content)

    # Add to RAG store
    store = get_vector_store()
    chunks_added = store.add_document(doc_id, content)

    result = {
        "document_id": doc_id,
        "auto_analysis": True,
        "keywords": keywords,
        "sentiment": sentiment,
        "rag_chunks_added": chunks_added,
    }
    _analyses[doc_id] = result
    await publish_analysis_completed(doc_id, result)


# Subscribe to events
subscribe_to_documents(_handle_document_created)
