"""In-memory document store."""
from datetime import datetime
from typing import Optional
import uuid


class DocumentStore:
    """Thread-safe in-memory document storage."""

    def __init__(self):
        self._documents: dict[str, dict] = {}

    def create(self, title: str, content: str, doc_type: str = "general") -> dict:
        doc_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        doc = {
            "id": doc_id,
            "title": title,
            "content": content,
            "doc_type": doc_type,
            "created_at": now,
            "updated_at": now,
            "word_count": len(content.split()),
        }
        self._documents[doc_id] = doc
        return doc

    def get(self, doc_id: str) -> Optional[dict]:
        return self._documents.get(doc_id)

    def list_all(self) -> list[dict]:
        return list(self._documents.values())

    def update(self, doc_id: str, **fields) -> Optional[dict]:
        doc = self._documents.get(doc_id)
        if not doc:
            return None
        for k, v in fields.items():
            if v is not None:
                doc[k] = v
        if "content" in fields and fields["content"] is not None:
            doc["word_count"] = len(fields["content"].split())
        doc["updated_at"] = datetime.utcnow().isoformat()
        return doc

    def delete(self, doc_id: str) -> bool:
        return self._documents.pop(doc_id, None) is not None

    def count(self) -> int:
        return len(self._documents)
