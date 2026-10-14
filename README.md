<div align="center">

# 📄 LocalRAG

**Private AI document assistant — upload PDFs, ask questions, get cited answers.**

Everything runs locally via Docker. No accounts, no cloud, no data leaves your machine.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](apps/api)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000.svg)](apps/web)

</div>

---

## ⚡ How It Works

1. **Upload PDF Documents** — text is extracted, chunked with semantic overlap, and embedded into Qdrant vectors.
2. **Ask Questions** — the RAG pipeline retrieves the most relevant passages via cosine similarity.
3. **Stream Cited Answers** — Ollama streams the response token-by-token with clickable `[S1]`, `[S2]` source citations.
4. **Zero Data Leakage** — documents and vectors live in local volumes; session state cleans up on demand.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Next.js 15 Web Frontend                  │
│             Responsive Glassmorphism UI (Port 8080)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / SSE Stream
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend (Port 8000)              │
│       Session Manager · Document Chunker · RAG Engine       │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
       ┌───────▼──────────────┐        ┌───────▼──────────────┐
       │   Qdrant Vector DB   │        │     Local Ollama     │
       │     (Port 6333)      │        │  (Host: Port 11434)  │
       └──────────────────────┘        └──────────────────────┘
```

> Pure microservices architecture — each service has its own self-contained `Dockerfile` and dependencies. Everything is orchestrated via `docker compose`.

---

## 🚀 Quick Start (Docker Only)

### Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/) installed.
- [Ollama](https://ollama.ai) installed and running on your host machine:
  ```bash
  ollama pull nomic-embed-text:latest
  ollama pull qwen2.5:0.5b
  ```

### Run LocalRAG

```bash
docker compose up --build -d
```

Open **[http://localhost:8080](http://localhost:8080)** in your browser to access the app!

---

## 📦 Services

| Service    | Port   | Description                                           |
|------------|--------|-------------------------------------------------------|
| **web**    | `8080` | Modern Next.js chat interface with dark glassmorphism |
| **api**    | `8000` | FastAPI backend & RAG pipeline (Host networking)      |
| **qdrant** | `6333` | Qdrant vector database for chunk embeddings           |
| **ollama** | `11434`| Local LLM and embedding server on host                |

---

## 📊 Observability (Optional)

To start Prometheus and Grafana monitoring:

```bash
docker compose --profile observability up -d
```

- **Grafana UI**: [http://localhost:3001](http://localhost:3001) (`admin` / `admin`)
- Includes pre-configured dashboards for retrieval latency, request throughput, and token generation speed.

---

## ⚙️ Configuration

Settings can be customized via `.env` (copy from `.env.example`):

| Variable              | Default                   | Description                     |
|-----------------------|---------------------------|---------------------------------|
| `CHAT_MODEL`          | `qwen2.5:0.5b`            | Ollama generation model         |
| `EMBEDDING_MODEL`     | `nomic-embed-text:latest` | Ollama text embedding model     |
| `MAX_UPLOAD_BYTES`    | `20971520`                | Max PDF upload size (20 MB)     |
| `SESSION_TTL_SECONDS` | `3600`                    | Inactive session expiry (1 hr)  |

### 🔄 How to Change AI Models / Comment changer de modèle

You can switch to any LLM or embedding model supported by Ollama:

1. **Pull the desired model with Ollama:**
   ```bash
   # Examples:
   ollama pull qwen2.5:1.5b
   # or
   ollama pull llama3.2:3b
   ```

2. **Update your `.env` file:**
   ```dotenv
   CHAT_MODEL=qwen2.5:1.5b
   EMBEDDING_MODEL=nomic-embed-text:latest
   ```

3. **Restart the containers to apply changes:**
   ```bash
   docker compose up -d
   ```

> **Note:** If you change the `EMBEDDING_MODEL` (e.g. to `bge-m3` or `mxbai-embed-large`), clear your session or re-upload your PDFs so Qdrant indexes vectors with the new embedding dimensions.


---

## 📁 Project Structure

```
.
├── apps/
│   ├── api/                      # Self-contained FastAPI microservice
│   │   ├── Dockerfile            # API container image
│   │   ├── requirements.txt      # Python dependencies
│   │   ├── main.py               # Endpoints & SSE streaming
│   │   ├── chunking.py           # Text chunking with overlap
│   │   └── settings.py           # Pydantic settings
│   └── web/                      # Self-contained Next.js microservice
│       ├── Dockerfile            # Frontend container image
│       ├── package.json          # Node dependencies
│       └── app/
│           ├── layout.tsx        # App root layout with Google Fonts
│           ├── page.tsx          # Modern chat canvas & sidebar
│           └── styles.css        # Glassmorphic dark design system
├── infra/
│   ├── grafana/                  # Provisioned datasources & dashboards
│   └── prometheus/               # Prometheus metrics scraper
├── tests/                        # Unit tests
├── docker-compose.yml            # Complete Docker composition
├── .env.example                  # Environment configuration template
└── README.md
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
