import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz

import httpx
from fastapi import FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, make_asgi_app

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
STORAGE_PATH = os.getenv("STORAGE_PATH", "/data/documents")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 20 * 1024 * 1024))
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8002").rstrip("/")

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
pdf_requests_total = Counter("pdf_requests_total", "Total requests to PDF microservice", ["route", "status"])
pdf_processing_seconds = Histogram("pdf_processing_seconds", "Time spent parsing and chunking PDF")

# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    text: str


def chunk_page(text: str, page_number: int, chunk_size: int = 1200, overlap: int = 180) -> list[TextChunk]:
    clean = " ".join(text.split())
    if not clean:
        return []
    chunks, start, index = [], 0, 0
    while start < len(clean):
        end = min(len(clean), start + chunk_size)
        if end < len(clean):
            boundary = clean.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(TextChunk(page_number, index, clean[start:end]))
        if end == len(clean):
            break
        start, index = max(end - overlap, start + 1), index + 1
    return chunks


# ---------------------------------------------------------------------------
# Session Document Storage
# ---------------------------------------------------------------------------
# session_id -> { doc_id: { ... } }
_sessions: dict[str, dict[str, dict]] = {}


def _get_session_docs(session_id: str | None) -> dict[str, dict]:
    sid = session_id or "default"
    if sid not in _sessions:
        _sessions[sid] = {}
    return _sessions[sid]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="LocalRAG PDF Microservice", version="1.0.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "pdf_microservice"}


@app.post("/api/v1/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    x_session_id: str | None = Header(None),
):
    """Upload a PDF, extract text, chunk it, index chunks via RAG service, and track metadata."""
    session_id = x_session_id or "default"
    docs = _get_session_docs(session_id)

    # Validate file type and extension
    if file.content_type not in {"application/pdf", "application/x-pdf"} and not (file.filename or "").lower().endswith(".pdf"):
        pdf_requests_total.labels(route="/api/v1/documents", status="415").inc()
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content or len(content) > MAX_UPLOAD_BYTES or not content.startswith(b"%PDF"):
        pdf_requests_total.labels(route="/api/v1/documents", status="400").inc()
        raise HTTPException(status_code=400, detail="Upload must be a valid PDF smaller than 20 MB")

    storage_key = f"{secrets.token_urlsafe(24)}.pdf"
    destination = Path(STORAGE_PATH) / storage_key
    destination.write_bytes(content)

    document_id = secrets.token_urlsafe(16)
    original_filename = Path(file.filename or "document.pdf").name

    try:
        with pdf_processing_seconds.time():
            pdf = fitz.open(stream=content, filetype="pdf")
            page_chunks = [
                chunk
                for page_no, page in enumerate(pdf, 1)
                for chunk in chunk_page(page.get_text(), page_no)
            ]

        if not page_chunks:
            destination.unlink(missing_ok=True)
            pdf_requests_total.labels(route="/api/v1/documents", status="422").inc()
            raise HTTPException(status_code=422, detail="No extractable text found in PDF")

        # Forward chunks to RAG microservice for embedding and vector storage
        index_payload = {
            "session_id": session_id,
            "document_id": document_id,
            "filename": original_filename,
            "chunks": [
                {
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "text": c.text,
                }
                for c in page_chunks
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(f"{RAG_SERVICE_URL}/api/v1/rag/index", json=index_payload)
                if res.status_code != 200:
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"RAG microservice indexing error: {res.text}",
                    )
        except httpx.RequestError as exc:
            destination.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to communicate with RAG microservice: {str(exc)}",
            )

        # Track document in session
        docs[document_id] = {
            "id": document_id,
            "filename": original_filename,
            "storage_key": storage_key,
            "sha256": hashlib.sha256(content).hexdigest(),
            "file_size": len(content),
            "page_count": len(pdf),
            "chunk_count": len(page_chunks),
            "status": "ready",
        }

        pdf_requests_total.labels(route="/api/v1/documents", status="201").inc()
        return {
            "document_id": document_id,
            "filename": original_filename,
            "page_count": len(pdf),
            "chunk_count": len(page_chunks),
            "status": "ready",
        }

    except HTTPException:
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        pdf_requests_total.labels(route="/api/v1/documents", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(exc)[:200]}")


@app.get("/api/v1/documents")
def list_documents(x_session_id: str | None = Header(None)):
    """List all documents for the specified session."""
    session_id = x_session_id or "default"
    docs = _get_session_docs(session_id)
    pdf_requests_total.labels(route="/api/v1/documents", status="200").inc()
    return [
        {
            "id": doc["id"],
            "filename": doc["filename"],
            "page_count": doc["page_count"],
            "chunk_count": doc["chunk_count"],
            "status": doc["status"],
        }
        for doc in docs.values()
    ]


@app.delete("/api/v1/documents/{document_id}", status_code=204)
async def delete_document(document_id: str, x_session_id: str | None = Header(None)):
    """Delete a document, unlinking its file and removing its vectors via RAG microservice."""
    session_id = x_session_id or "default"
    docs = _get_session_docs(session_id)
    doc = docs.pop(document_id, None)
    if not doc:
        pdf_requests_total.labels(route="/api/v1/documents/{id}", status="404").inc()
        raise HTTPException(status_code=404, detail="Document not found")

    storage_key = doc.get("storage_key", "")
    if storage_key:
        (Path(STORAGE_PATH) / storage_key).unlink(missing_ok=True)

    # Call RAG service to delete vectors
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.delete(
                f"{RAG_SERVICE_URL}/api/v1/rag/documents/{document_id}",
                headers={"X-Session-Id": session_id},
            )
    except Exception:
        pass  # Best effort

    pdf_requests_total.labels(route="/api/v1/documents/{id}", status="204").inc()
    return Response(status_code=204)


@app.delete("/api/v1/session", status_code=204)
async def delete_session(x_session_id: str | None = Header(None)):
    """Clear all documents for session."""
    session_id = x_session_id or "default"
    docs = _sessions.pop(session_id, {})
    for doc in docs.values():
        storage_key = doc.get("storage_key", "")
        if storage_key:
            (Path(STORAGE_PATH) / storage_key).unlink(missing_ok=True)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.delete(f"{RAG_SERVICE_URL}/api/v1/rag/sessions/{session_id}")
    except Exception:
        pass

    pdf_requests_total.labels(route="/api/v1/session", status="204").inc()
    return Response(status_code=204)
