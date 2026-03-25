"""Structured error types for the pipeline."""


class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    def __init__(self, message: str, code: str = "PIPELINE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class LLMChainError(PipelineError):
    def __init__(self, message: str, chain_step: str = "unknown"):
        self.chain_step = chain_step
        super().__init__(message, code="LLM_CHAIN_ERROR")


class GuardrailViolation(PipelineError):
    def __init__(self, message: str, violations: list[str] = None):
        self.violations = violations or []
        super().__init__(message, code="GUARDRAIL_VIOLATION")


class DocumentNotFoundError(PipelineError):
    def __init__(self, doc_id: str):
        super().__init__(f"Document {doc_id} not found", code="DOCUMENT_NOT_FOUND")
