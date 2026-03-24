"""LangChain chains for document analysis pipeline."""
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnableSequence, RunnablePassthrough, RunnableParallel, RunnableLambda
from pydantic import BaseModel, Field
import re
import json


class SafeJsonParser(RunnableLambda):
    """JSON parser with retry on failure."""
    def __init__(self):
        self._parser = JsonOutputParser()
        super().__init__(self._safe_parse)

    def _safe_parse(self, input_text):
        try:
            return self._parser.invoke(input_text)
        except Exception:
            # Try to extract JSON from the text
            match = re.search(r'\{[\s\S]*\}', str(input_text))
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            # Return a safe default
            return {"summary": "Analysis completed but output parsing failed.", "key_topics": [], "sentiment": "neutral", "risk_level": "low", "action_items": ["Review raw output manually"]}


class DocumentAnalysis(BaseModel):
    summary: str = Field(description="3-sentence executive summary")
    key_topics: list[str] = Field(description="Top 5 key topics")
    sentiment: str = Field(description="positive, negative, or neutral")
    risk_level: str = Field(description="low, medium, or high")
    action_items: list[str] = Field(description="Recommended actions")


# Chain 1: Extract & Summarize
extract_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a senior document analyst. Extract key information concisely."),
    ("human", "Analyze this document and provide a structured analysis:\n\n{document}\n\nRespond in JSON with: summary, key_topics (list of 5), sentiment (positive/negative/neutral), risk_level (low/medium/high), action_items (list of 3)")
])

# Chain 2: Quality Assessment
quality_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a quality reviewer. Assess the analysis quality."),
    ("human", "Review this analysis:\n{analysis}\n\nRate quality 1-10 and suggest improvements. Respond in JSON with: score (int), improvements (list)")
])

# Chain 3: Final Report
report_prompt = ChatPromptTemplate.from_template(
    "Based on this analysis:\n{analysis}\n\nAnd quality review:\n{review}\n\nGenerate a final executive report with: title, executive_summary, findings (list), recommendations (list), risk_assessment."
)


def create_analysis_chain(llm):
    """Create the full LangChain analysis pipeline."""
    extract_chain = extract_prompt | llm | SafeJsonParser()
    quality_chain = quality_prompt | llm | SafeJsonParser()
    report_chain = report_prompt | llm | StrOutputParser()
    return extract_chain, quality_chain, report_chain


def create_chains_from_registry(llm, registry):
    """Create chains using templates from the prompt registry."""
    extract_tmpl = registry.get_active("extract_analysis")
    quality_tmpl = registry.get_active("quality_review")
    report_tmpl = registry.get_active("final_report")

    if extract_tmpl and quality_tmpl and report_tmpl:
        ext_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a senior document analyst."),
            ("human", extract_tmpl.template)
        ])
        qual_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a quality reviewer."),
            ("human", quality_tmpl.template)
        ])
        rep_prompt = ChatPromptTemplate.from_template(report_tmpl.template)

        return (
            ext_prompt | llm | SafeJsonParser(),
            qual_prompt | llm | SafeJsonParser(),
            rep_prompt | llm | StrOutputParser(),
        )
    # Fallback to hardcoded prompts
    return create_analysis_chain(llm)


def create_simple_chain(llm):
    """Create a simple chain for quick analysis."""
    prompt = ChatPromptTemplate.from_template(
        "Summarize this document in 3 sentences:\n\n{document}"
    )
    return prompt | llm | StrOutputParser()


def create_agent_chain(llm, tools):
    """Create a LangChain agent that dynamically selects tools."""
    try:
        from langchain.agents import create_tool_calling_agent, AgentExecutor
    except ImportError:
        return None

    agent_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a senior document analyst with expertise in legal, financial, and compliance documents.

You have access to tools for:
- Extracting keywords from text
- Detecting legal/financial risk terms
- Analyzing sentiment
- Counting document structure
- Retrieving similar documents from the knowledge base

Based on the document type and content, decide which tools to use. Not every document needs every tool.
For legal documents: prioritize risk detection and keyword extraction.
For financial documents: prioritize sentiment analysis and keyword extraction.
For compliance documents: use all tools including RAG retrieval.

After using tools, provide a comprehensive analysis in JSON format with:
{{"summary": "3 sentences", "key_topics": ["list"], "sentiment": "pos/neg/neutral", "risk_level": "low/med/high", "action_items": ["list"], "tools_used": ["list of tools you called"]}}"""),
        ("human", "Analyze this document:\n\n{document}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    try:
        agent = create_tool_calling_agent(llm, tools, agent_prompt)
        executor = AgentExecutor(
            agent=agent, tools=tools, verbose=True,
            max_iterations=5, return_intermediate_steps=True
        )
        return executor
    except Exception:
        # Fallback: return None, caller will use manual chain
        return None


def create_composed_chain(llm):
    """Create a composed chain with parallel fan-out."""
    extract_chain = extract_prompt | llm | SafeJsonParser()

    composed = RunnableParallel(
        extraction=extract_chain,
        quality=quality_prompt | llm | SafeJsonParser(),
    )
    return composed
