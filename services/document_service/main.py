"""Document Service - FastAPI app for document CRUD operations."""
from fastapi import FastAPI, HTTPException
from .models import DocumentCreate, DocumentUpdate, Document
from .store import DocumentStore
from .events import publish_document_created, publish_document_deleted

app = FastAPI(title="Document Service", version="1.0.0")
store = DocumentStore()


@app.get("/documents")
async def list_documents():
    docs = store.list_all()
    return {"documents": docs, "count": len(docs)}


@app.post("/documents", status_code=201)
async def create_document(body: DocumentCreate):
    doc = store.create(title=body.title, content=body.content, doc_type=body.doc_type)
    await publish_document_created(doc)
    return {"document": doc, "message": "Document created"}


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    doc = store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document": doc}


@app.put("/documents/{doc_id}")
async def update_document(doc_id: str, body: DocumentUpdate):
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    doc = store.update(doc_id, **updates)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document": doc, "message": "Document updated"}


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    deleted = store.delete(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    await publish_document_deleted(doc_id)
    return {"message": "Document deleted"}
