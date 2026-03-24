"""Analysis Service - FastAPI app for LangChain document analysis."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio

from .chains import create_analysis_chain, create_simple_chain, create_agent_chain, create_composed_chain, create_chains_from_registry
from .tools import extract_keywords, detect_risk_terms, analyze_sentiment_basic, count_sections, ANALYSIS_TOOLS
from .bedrock_client import get_llm
from .events import publish_analysis_completed, subscribe_to_documents
from .rag import get_vector_store
from .callbacks import ObservabilityHandler, GlobalObservability
from .guardrails import InputGuardrails, OutputGuardrails
from services.mlops.metrics import MetricsTracker
from services.mlops import StructuredLogger

app = FastAPI(title="Analysis Service", version="1.0.0")
metrics = MetricsTracker()
logger = StructuredLogger()
_analyses: dict[str, dict] = {}
_prompt_registry = None


async def run_tools_parallel(content: str) -> dict:
    """Run all analysis tools in parallel."""
    loop = asyncio.get_event_loop()
    keywords_task = loop.run_in_executor(None, lambda: extract_keywords.invoke(content))
    risks_task = loop.run_in_executor(None, lambda: detect_risk_terms.invoke(content))
    sentiment_task = loop.run_in_executor(None, lambda: analyze_sentiment_basic.invoke(content))
    structure_task = loop.run_in_executor(None, lambda: count_sections.invoke(content))

    keywords, risks, sentiment, structure = await asyncio.gather(
        keywords_task, risks_task, sentiment_task, structure_task
    )
    return {"keywords": keywords, "risks": risks, "sentiment": sentiment, "structure": structure}


def set_prompt_registry(registry):
    global _prompt_registry
    _prompt_registry = registry


class AnalyzeRequest(BaseModel):
    document_id: str = Field(default="direct")
    content: str = Field(..., min_length=10, max_length=100000)
    mode: str = Field(default="full", description="full or quick")


@app.post("/analyze")
async def analyze_document(body: AnalyzeRequest):
    obs = GlobalObservability()

    # Input guardrails
    input_check = InputGuardrails.validate(body.content)
    if input_check.issues:
        for issue in input_check.issues:
            logger.warn("analysis_service", f"Input guardrail: {issue}")

    llm = get_llm()

    # Run tools in parallel
    parallel_results = await run_tools_parallel(body.content)
    tool_results = {
        "keywords": parallel_results["keywords"],
        "risk_terms": parallel_results["risks"],
        "sentiment": parallel_results["sentiment"],
        "structure": parallel_results["structure"],
    }

    if body.mode == "quick":
        handler = ObservabilityHandler(chain_step="quick_summary")
        chain = create_simple_chain(llm)
        summary = chain.invoke({"document": body.content}, config={"callbacks": [handler]})
        obs.add_records(handler.records)
        result = {
            "document_id": body.document_id,
            "summary": summary,
            "tools": tool_results,
            "mode": "quick",
        }
    else:
        try:
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
                # Fallback to manual chains — try registry prompts first
                if _prompt_registry:
                    chains = create_chains_from_registry(llm, _prompt_registry)
                else:
                    chains = create_analysis_chain(llm)
                extract_chain, quality_chain, report_chain = chains

                # Step 1: Extract & analyze with observability
                extract_handler = ObservabilityHandler(chain_step="extraction")
                analysis = extract_chain.invoke({"document": body.content}, config={"callbacks": [extract_handler]})
                obs.add_records(extract_handler.records)

            # Output guardrails on analysis
            if isinstance(analysis, dict):
                output_check = OutputGuardrails.validate(analysis, body.content)
                if not output_check.valid:
                    for issue in output_check.issues:
                        logger.warn("analysis_service", f"Output guardrail: {issue}")

            # Step 2: Quality review (always run)
            if _prompt_registry:
                chains = create_chains_from_registry(llm, _prompt_registry)
            else:
                chains = create_analysis_chain(llm)
            _, quality_chain, report_chain = chains
            analysis_str = json.dumps(analysis) if isinstance(analysis, dict) else analysis

            quality_handler = ObservabilityHandler(chain_step="quality_review")
            quality = quality_chain.invoke({"analysis": analysis_str}, config={"callbacks": [quality_handler]})
            obs.add_records(quality_handler.records)

            # Step 3: Final report
            quality_str = json.dumps(quality)
            report_handler = ObservabilityHandler(chain_step="report")
            report = report_chain.invoke({"analysis": analysis_str, "review": quality_str}, config={"callbacks": [report_handler]})
            obs.add_records(report_handler.records)

        except Exception as e:
            logger.error("analysis_service", f"Chain failed: {str(e)}")
            metrics.record("analysis_errors", 1.0)
            # Fallback to tool-only analysis
            analysis = {
                "summary": "LLM chain failed, using tool-only analysis",
                "key_topics": [],
                "sentiment": tool_results.get("sentiment", "neutral"),
                "risk_level": "unknown",
                "action_items": ["Review document manually"],
            }
            quality = {"score": 0, "improvements": ["LLM chain was unavailable"]}
            report = "Tool-only analysis — LLM chain failed"
            agent_used = False

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

    # Add guardrail warnings to result
    if input_check.issues:
        result["guardrail_warnings"] = input_check.issues

    # Add document to RAG vector store
    store = get_vector_store()
    chunks_added = store.add_document(body.document_id, body.content)
    result["rag_chunks_added"] = chunks_added

    _analyses[body.document_id] = result
    await publish_analysis_completed(body.document_id, result)
    return result


@app.post("/analyze/stream")
async def analyze_stream(body: AnalyzeRequest):
    """Streaming analysis with Server-Sent Events."""
    async def event_generator():
        content = body.content

        yield f"data: {json.dumps({'step': 'started', 'message': 'Analysis pipeline started'})}\n\n"
        await asyncio.sleep(0.3)

        # Tools phase
        yield f"data: {json.dumps({'step': 'tools', 'message': 'Running analysis tools...'})}\n\n"
        tools_result = await run_tools_parallel(content)
        yield f"data: {json.dumps({'step': 'tools_done', 'keywords': tools_result['keywords'][:200]})}\n\n"
        await asyncio.sleep(0.2)

        # Chain phase
        yield f"data: {json.dumps({'step': 'extraction', 'message': 'Extracting key information...'})}\n\n"
        llm = get_llm()
        extract_chain, quality_chain, report_chain = create_analysis_chain(llm)

        try:
            analysis = extract_chain.invoke({"document": content})
            yield f"data: {json.dumps({'step': 'extraction_done', 'summary': str(analysis.get('summary', ''))[:200]})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'step': 'quality', 'message': 'Quality review...'})}\n\n"
            quality = quality_chain.invoke({"analysis": json.dumps(analysis)})
            yield f"data: {json.dumps({'step': 'quality_done', 'score': quality.get('score', 0)})}\n\n"
            await asyncio.sleep(0.2)

            yield f"data: {json.dumps({'step': 'report', 'message': 'Generating report...'})}\n\n"
            # Stream report word by word
            report_text = report_chain.invoke({"analysis": json.dumps(analysis), "review": json.dumps(quality)})
            words = report_text.split()
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i:i+5])
                yield f"data: {json.dumps({'step': 'report_chunk', 'chunk': chunk})}\n\n"
                await asyncio.sleep(0.05)
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'step': 'complete', 'message': 'Analysis complete'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
