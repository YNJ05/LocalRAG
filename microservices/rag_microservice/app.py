import os
from uuid import NAMESPACE_URL, uuid5

import requests
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "localrag_chunks")
DEFAULT_TOP_K = int(os.getenv("TOP_K", "5"))

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
rag_requests_total = Counter("rag_requests_total", "Total requests to RAG microservice", ["route", "status"])
rag_indexing_seconds = Histogram("rag_indexing_seconds", "Time spent indexing document chunks")
rag_retrieval_seconds = Histogram("rag_retrieval_seconds", "Time spent retrieving relevant chunks from Qdrant")


def _qdrant() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, timeout=30, check_compatibility=False)


def _ensure_collection(client: QdrantClient, dimensions: int) -> None:
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
        )
        client.create_payload_index(QDRANT_COLLECTION, "session_id", "keyword")
        client.create_payload_index(QDRANT_COLLECTION, "document_id", "keyword")


def _embed_texts(texts: list[str]) -> list[list[float]]:
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embeddings"]


def _embed_single(text: str) -> list[float]:
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ChunkInput(BaseModel):
    page_number: int
    chunk_index: int
    text: str


class IndexRequest(BaseModel):
    session_id: str
    document_id: str
    filename: str
    chunks: list[ChunkInput]


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    session_id: str
    document_id: str | None = None
    top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=20)


app = FastAPI(title="LocalRAG RAG Microservice", version="1.0.0")
app.mount("/metrics", make_asgi_app())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live")
def live():
    return {"status": "ok", "service": "rag_microservice"}


@app.post("/api/v1/rag/index")
def index_document_chunks(payload: IndexRequest):
    """Generate embeddings for text chunks and store them in Qdrant collection."""
    if not payload.chunks:
        raise HTTPException(status_code=400, detail="No chunks provided for indexing")

    try:
        with rag_indexing_seconds.time():
            texts = [c.text for c in payload.chunks]
            embeddings = _embed_texts(texts)

            client = _qdrant()
            _ensure_collection(client, len(embeddings[0]))

            points = [
                PointStruct(
                    id=str(uuid5(NAMESPACE_URL, f"{payload.document_id}:{c.page_number}:{c.chunk_index}")),
                    vector=vector,
                    payload={
                        "session_id": payload.session_id,
                        "document_id": payload.document_id,
                        "filename": payload.filename,
                        "chunk_id": f"{payload.document_id}:{c.page_number}:{c.chunk_index}",
                        "page_number": c.page_number,
                        "chunk_index": c.chunk_index,
                        "text": c.text,
                        "embedding_model": EMBEDDING_MODEL,
                    },
                )
                for c, vector in zip(payload.chunks, embeddings)
            ]

            client.upsert(QDRANT_COLLECTION, points, wait=True)

        rag_requests_total.labels(route="/api/v1/rag/index", status="200").inc()
        return {
            "status": "indexed",
            "document_id": payload.document_id,
            "chunks_count": len(points),
        }

    except Exception as exc:
        rag_requests_total.labels(route="/api/v1/rag/index", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc!s}")


@app.post("/api/v1/rag/query")
def query_relevant_chunks(payload: QueryRequest):
    """Embed the query and retrieve the top_k matching chunks from Qdrant."""
    try:
        with rag_retrieval_seconds.time():
            client = _qdrant()
            if not client.collection_exists(QDRANT_COLLECTION):
                return {"sources": [], "count": 0}

            query_vector = _embed_single(payload.question)

            conditions = [FieldCondition(key="session_id", match=MatchValue(value=payload.session_id))]
            if payload.document_id:
                conditions.append(FieldCondition(key="document_id", match=MatchValue(value=payload.document_id)))

            results = client.query_points(
                QDRANT_COLLECTION,
                query=query_vector,
                query_filter=Filter(must=conditions),
                limit=payload.top_k,
                with_payload=True,
            ).points

            sources = [
                {
                    "source_id": f"S{i}",
                    "document_id": point.payload.get("document_id", ""),
                    "filename": point.payload.get("filename", "Unknown"),
                    "page_number": point.payload.get("page_number", 1),
                    "chunk_index": point.payload.get("chunk_index", 0),
                    "excerpt": point.payload.get("text", "")[:500],
                    "text": point.payload.get("text", ""),
                    "score": round(float(point.score), 4),
                }
                for i, point in enumerate(results, 1)
            ]

        rag_requests_total.labels(route="/api/v1/rag/query", status="200").inc()
        return {"sources": sources, "count": len(sources)}

    except Exception as exc:
        rag_requests_total.labels(route="/api/v1/rag/query", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc!s}")


@app.delete("/api/v1/rag/documents/{document_id}", status_code=204)
def delete_document_vectors(document_id: str, x_session_id: str | None = Header(None)):
    """Delete all vector points belonging to a specific document."""
    try:
        client = _qdrant()
        if client.collection_exists(QDRANT_COLLECTION):
            must_conditions = [FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            if x_session_id:
                must_conditions.append(FieldCondition(key="session_id", match=MatchValue(value=x_session_id)))

            client.delete(
                QDRANT_COLLECTION,
                points_selector=Filter(must=must_conditions),
                wait=True,
            )
        rag_requests_total.labels(route="/api/v1/rag/documents/{id}", status="204").inc()
        return Response(status_code=204)
    except Exception as exc:
        rag_requests_total.labels(route="/api/v1/rag/documents/{id}", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Failed to delete document vectors: {exc!s}")


@app.delete("/api/v1/rag/sessions/{session_id}", status_code=204)
def delete_session_vectors(session_id: str):
    """Delete all vector points belonging to a session."""
    try:
        client = _qdrant()
        if client.collection_exists(QDRANT_COLLECTION):
            client.delete(
                QDRANT_COLLECTION,
                points_selector=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))]),
                wait=True,
            )
        rag_requests_total.labels(route="/api/v1/rag/sessions/{id}", status="204").inc()
        return Response(status_code=204)
    except Exception as exc:
        rag_requests_total.labels(route="/api/v1/rag/sessions/{id}", status="500").inc()
        raise HTTPException(status_code=500, detail=f"Failed to delete session vectors: {exc!s}")
