# LocalRAG

A private, offline document assistant built with a decoupled microservices architecture. Upload PDFs, ask questions, and receive streamed answers with exact source citations.

---

## Architecture

- **Frontend**: Streamlit web interface (`:8501`)
- **PDF Microservice**: PDF text extraction, chunking, and file storage (`:8001`)
- **RAG Microservice**: Qdrant vector database indexing and semantic retrieval (`:8002`)
- **Chat Microservice**: Context assembly and LLM response generation (`:8003`)
- **Vector DB**: Qdrant (`:6333`)
- **Local LLM & Embeddings**: Ollama (`:11434`)
  - Embedding Model: `nomic-embed-text:latest`
  - Generation Model: `qwen2.5:0.5b`
- **Observability**: Prometheus (`:9090`) & Grafana (`:3001`)

---

## Quick Start (Docker Compose)

### 1. Ensure Ollama models are pulled
```bash
ollama pull nomic-embed-text:latest
ollama pull qwen2.5:0.5b
```

### 2. Start all services
```bash
docker compose up -d
```

### 3. Access the application
- **Web UI**: [http://localhost:8501](http://localhost:8501)
- **Grafana Dashboards**: [http://localhost:3001](http://localhost:3001)
- **Prometheus Metrics**: [http://localhost:9090](http://localhost:9090)

---

## Kubernetes & Helm

### Deploy with Helm
```bash
helm upgrade --install localrag ./helm/localrag -n localrag --create-namespace
```

### Deploy with standard manifests
```bash
kubectl apply -f k8s/
```

### Access with Ingress
Add to `/etc/hosts`:
```text
127.0.0.1 localrag.local
```
Then visit [http://localrag.local](http://localrag.local).

---

## CI/CD & DevSecOps

The GitHub Actions workflow automatically runs:
- **Gitleaks**: Secret detection
- **Ruff**: Code linting
- **Helm Lint**: Chart validation
- **Trivy**: Container vulnerability scanning
- **GHCR**: Multi-service image publishing
