<div align="center">

# 📄 LocalRAG — Enterprise Cloud-Native Architecture

**Decoupled, private RAG platform engineered with microservices, Helm, Kubernetes, ArgoCD GitOps, and Prometheus/Grafana observability.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-Microservices-009688.svg)](microservices)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B.svg)](frontend)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Manifests-326CE5.svg)](k8s)
[![Helm](https://img.shields.io/badge/Helm-Chart%20v3-0F1689.svg)](helm/localrag)
[![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-EF7B4D.svg)](argocd/application.yaml)
[![DevSecOps](https://img.shields.io/badge/Security-Trivy%20%7C%20Gitleaks-brightgreen.svg)](.github/workflows/ci.yml)

</div>

---

## ⚡ System Architecture

```
                                    ┌───────────────────────┐
                                    │   NGINX Ingress       │
                                    │  (localrag.local)     │
                                    └───────────┬───────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │ /                            │ /api/v1/documents            │ /api/v1/chat
                 ▼                              ▼                              ▼
      ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
      │   ui-frontend       │        │  pdf-microservice   │        │  chat-microservice  │
      │   (Streamlit :8501) │        │   (FastAPI :8001)   │        │   (FastAPI :8003)   │
      └─────────────────────┘        └──────────┬──────────┘        └──────────┬──────────┘
                                                │ Index Chunks                 │ Query Sources
                                                ▼                              ▼
                                     ┌────────────────────────────────────────────────────┐
                                     │                  rag-microservice                  │
                                     │                  (FastAPI :8002)                   │
                                     └──────────┬──────────────────────────────┬──────────┘
                                                │ Store Vectors                │ Embeddings & Gen
                                                ▼                              ▼
                                     ┌─────────────────────┐        ┌─────────────────────┐
                                     │  Qdrant Vector DB   │        │    Ollama Server    │
                                     │       (:6333)       │        │      (:11434)       │
                                     └─────────────────────┘        └─────────────────────┘
```

### Models Used
- **Embeddings**: `nomic-embed-text:latest`
- **LLM Reasoning**: `qwen2.5:0.5b`

---

## 📁 Repository Structure

```
├── .github/workflows/
│   └── ci.yml               # DevSecOps: Gitleaks, Ruff, Helm lint, Trivy scan, GHCR publish
├── argocd/
│   └── application.yaml     # GitOps Continuous Delivery manifest
├── frontend/
│   ├── Dockerfile
│   ├── app_ui.py            # Streamlit UI with Apple/Jenkins dark theme & Ubuntu Sans font
│   └── requirements.txt
├── helm/localrag/
│   ├── Chart.yaml           # Helm v3 Chart definition
│   ├── values.yaml          # Configurable replicas, resource limits, and ingress settings
│   └── templates/           # Parameterized Kubernetes templates
├── k8s/
│   ├── namespace.yaml
│   ├── ingress.yaml         # NGINX Ingress controller configuration
│   ├── ollama-deployment.yaml
│   ├── pdf-deployment.yaml
│   ├── rag-deployment.yaml
│   ├── chat-deployment.yaml
│   └── ui-deployment.yaml
├── microservices/
│   ├── chat_microservice/   # Prompt formulation, LLM generation, SSE streaming
│   ├── pdf_microservice/    # PDF parsing, semantic chunking, doc storage
│   └── rag_microservice/    # Qdrant vector operations & Ollama embeddings
├── monitoring/
│   ├── grafana/             # Datasources and pre-configured dashboards
│   └── prometheus/          # Scrape configurations for all microservices
├── docker-compose.yml       # Local development orchestration with host networking
└── README.md
```

---

## ☸️ Cloud-Native Deployment (Helm & Kubernetes)

### 1. Production Deployment with Helm
Deploy the complete stack to any Kubernetes cluster (Minikube, Kind, K3s, EKS, GKE) with a single command:

```bash
# Lint the chart
helm lint ./helm/localrag

# Install or upgrade the release
helm upgrade --install localrag ./helm/localrag \
  --namespace localrag \
  --create-namespace
```

### 2. Ingress & Domain Routing
Map the ingress hostname to your cluster or localhost:
```bash
echo "127.0.0.1 localrag.local" | sudo tee -a /etc/hosts
```
Once mapped, open **`http://localrag.local`** to access the Streamlit UI, or send API requests directly to **`http://localrag.local/api/v1/chat`**.

### 3. GitOps with ArgoCD
Deploy and automatically synchronize changes via ArgoCD:
```bash
kubectl apply -f argocd/application.yaml
```
ArgoCD will automatically monitor the `helm/localrag` directory, reconcile cluster drift, and perform zero-touch continuous deployment.

---

## 🔒 DevSecOps CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) executes an automated security and delivery lifecycle:

1. **Secret Detection**: Runs **Gitleaks** on all commits to prevent hardcoded credentials or API keys.
2. **Static Analysis & Linting**: Executes **Ruff** across all microservices and frontend code.
3. **Helm Verification**: Lints and performs dry-run template rendering on `helm/localrag`.
4. **Container Vulnerability Scanning**: Scans every built container image using **Trivy** for `CRITICAL` and `HIGH` CVEs.
5. **Registry Publishing**: Automatically packages and pushes multi-service container images to **GitHub Container Registry (`ghcr.io`)**.

---

## 💻 Local Development (Docker Compose)

Start all services locally with host networking and Prometheus/Grafana monitoring:

```bash
docker compose up -d
```

### Local Endpoints
- **Streamlit Web UI**: [http://localhost:8501](http://localhost:8501)
- **PDF Microservice**: [http://localhost:8001/health/live](http://localhost:8001/health/live)
- **RAG Microservice**: [http://localhost:8002/health/live](http://localhost:8002/health/live)
- **Chat Microservice**: [http://localhost:8003/health/live](http://localhost:8003/health/live)
- **Prometheus**: [http://localhost:9090](http://localhost:9090)
- **Grafana**: [http://localhost:3001](http://localhost:3001) (`admin` / `admin`)
