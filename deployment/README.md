# Deployment Guide

## Option A — Local Docker Compose (recommended for demo)

**Requirements:** Docker Desktop ≥ 24, 16 GB RAM (Ollama + Elasticsearch are memory-hungry)

```bash
# 1. Copy and fill in secrets
cp .env.example .env
# Edit .env — at minimum change SECRET_KEY

# 2. Start all services (first run pulls images + builds — can take 5–10 min)
docker compose up -d --build

# 3. Pull the required Ollama models (run once after first start)
docker compose exec ollama ollama pull llama3.1
docker compose exec ollama ollama pull nomic-embed-text

# 4. Open the app
open http://localhost        # frontend (Nginx)
open http://localhost:8000   # backend API docs (FastAPI Swagger)
```

**Observability stack (optional — adds Prometheus + Grafana + Jaeger):**
```bash
docker compose -f docker-compose.observability.yml up -d
open http://localhost:3001   # Grafana (admin/admin)
open http://localhost:16686  # Jaeger traces
```

---

## Option B — Railway (backend) + Vercel (frontend)

### Backend on Railway

1. Go to https://railway.app and create a new project
2. Add services:
   - **PostgreSQL** (Railway add-on)
   - **Redis** (Railway add-on)
   - **GitHub repo** → select this repo, root directory: `backend/`
3. Railway auto-detects the `Dockerfile` and `deployment/railway.toml`
4. Set environment variables in Railway dashboard (copy from `.env.example`):
   - `SECRET_KEY` — use a strong random value
   - `POSTGRES_URL` — Railway provides this automatically for the PG add-on
   - `REDIS_URL` — Railway provides this automatically for the Redis add-on
   - `QDRANT_HOST`, `NEO4J_URI`, `ELASTICSEARCH_URL` — use cloud free tiers (see below)
   - `OLLAMA_HOST` / `OLLAMA_PORT` — Ollama cannot run on Railway; use Groq free tier instead
5. Railway gives you a URL like `https://yourapp.up.railway.app`

**Free cloud alternatives for self-hosted services:**
| Service | Free tier option |
|---------|-----------------|
| Qdrant | https://qdrant.tech/cloud — 1 GB free cluster |
| Neo4j | https://neo4j.com/cloud/aura-free — 200K nodes |
| Elasticsearch | https://www.elastic.co/cloud — 14-day trial |
| Ollama LLM | Use [Groq](https://console.groq.com) free API instead — change `CHAT_MODEL` in `rag.py` |

### Frontend on Vercel

1. Go to https://vercel.com → New Project → import this GitHub repo
2. Set root directory to `frontend/`
3. Vercel auto-detects Vite
4. Add environment variables:
   - `VITE_API_URL` = `https://yourapp.up.railway.app`
   - `VITE_WS_URL` = `wss://yourapp.up.railway.app`
5. Copy `deployment/vercel.json` to `frontend/vercel.json`
6. Deploy — Vercel gives you `https://yourapp.vercel.app`

---

## CI/CD (GitHub Actions)

Two workflows are pre-configured:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `.github/workflows/ci.yml` | Push / PR to main/develop | Lint backend, type-check + build frontend, build Docker images |
| `.github/workflows/deploy.yml` | Push to main | Deploy backend to Railway, frontend to Vercel |

**Required GitHub Secrets for deploy workflow:**

| Secret | How to get it |
|--------|---------------|
| `RAILWAY_TOKEN` | Railway dashboard → Settings → Tokens |
| `VERCEL_TOKEN` | Vercel → Account Settings → Tokens |
| `VERCEL_ORG_ID` | `vercel whoami --json` |
| `VERCEL_PROJECT_ID` | `vercel project ls --json` |
| `VITE_API_URL` | Your Railway backend URL |
| `VITE_WS_URL` | Your Railway backend WSS URL |

---

## First-time setup after deployment

```bash
# Run migrations (Railway runs these automatically via entrypoint.sh)
# For manual run:
alembic upgrade head

# Pull Ollama models (if self-hosting Ollama)
ollama pull llama3.1
ollama pull nomic-embed-text

# Create your first user via the login page (register endpoint is open)
```

---

## Resource requirements

| Component | Min RAM | Notes |
|-----------|---------|-------|
| Backend (FastAPI) | 512 MB | |
| Postgres | 256 MB | |
| Redis | 128 MB | |
| Qdrant | 512 MB | |
| Neo4j | 1 GB | |
| Elasticsearch | 1 GB | `-Xms512m -Xmx512m` set in compose |
| Ollama (llama3.1) | 6–8 GB | CPU-only; GPU recommended |
| **Total** | **~10 GB** | Local Docker setup |
