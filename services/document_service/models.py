"""Pydantic models for document service."""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=10)
    doc_type: str = Field(default="general")

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v):
        allowed = {"general", "contract", "financial", "compliance", "legal", "report"}
        if v not in allowed:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(allowed))}")
        return v


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    doc_type: Optional[str] = None

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v):
        if v is None:
            return v
        allowed = {"general", "contract", "financial", "compliance", "legal", "report"}
        if v not in allowed:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(allowed))}")
        return v


class Document(BaseModel):
    id: str
    title: str
    content: str
    doc_type: str
    created_at: str
    updated_at: str
    word_count: int


class DocumentResponse(BaseModel):
    document: Document
    message: str = "success"
