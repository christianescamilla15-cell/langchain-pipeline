"""LangChain chains for document analysis pipeline."""
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.runnables import RunnableSequence, RunnablePassthrough
from pydantic import BaseModel, Field


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
    extract_chain = extract_prompt | llm | JsonOutputParser()
    quality_chain = quality_prompt | llm | JsonOutputParser()
    report_chain = report_prompt | llm | StrOutputParser()
    return extract_chain, quality_chain, report_chain


def create_simple_chain(llm):
    """Create a simple chain for quick analysis."""
    prompt = ChatPromptTemplate.from_template(
        "Summarize this document in 3 sentences:\n\n{document}"
    )
    return prompt | llm | StrOutputParser()
