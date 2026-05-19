# Enterprise AI OS — Project Guide

A full-stack, self-hosted enterprise AI platform built across 11 phases. Combines multi-agent LLM orchestration, adaptive retrieval, layered memory, a knowledge graph, meeting intelligence, a browser agent, voice AI, evaluation metrics, and production deployment — all using free/open-source tools with no mandatory external API keys.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Folder Structure](#folder-structure)
3. [Architecture Overview](#architecture-overview)
4. [Component Workflows](#component-workflows)
   - [Authentication](#1-authentication)
   - [Document Ingestion](#2-document-ingestion)
   - [Multi-Agent Chat](#3-multi-agent-chat)
   - [Adaptive Retrieval Engine](#4-adaptive-retrieval-engine)
   - [Layered Memory System](#5-layered-memory-system)
   - [Knowledge Graph](#6-knowledge-graph)
   - [Meeting Intelligence](#7-meeting-intelligence)
   - [Browser Agent](#8-browser-agent)
   - [Voice AI](#9-voice-ai)
   - [Evaluation & Observability](#10-evaluation--observability)
5. [API Reference](#api-reference)
6. [Frontend Pages](#frontend-pages)
7. [Running the Project](#running-the-project)
   - [Option A — Local Dev (recommended for development)](#option-a--local-dev-recommended-for-development)
   - [Option B — Full Docker Compose](#option-b--full-docker-compose)
8. [Environment Variables](#environment-variables)
9. [Database Migrations](#database-migrations)
10. [Deployment](#deployment)

---

## Tech Stack

### Backend

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API framework | **FastAPI** | Async REST + SSE + WebSocket |
| Agent orchestration | **LangGraph** | Stateful multi-agent pipeline with conditional retry |
| Primary LLM | **Ollama** (`llama3.1`) | Local inference — no API key needed |
| Embeddings | **Ollama** (`nomic-embed-text`, 768-dim) | Local embeddings |
| Vector DB | **Qdrant** | Similarity search for documents + memory |
| Keyword search | **Elasticsearch** | BM25 full-text search |
| Graph DB | **Neo4j** | Entity/relationship knowledge graph |
| Cache / Pub-Sub | **Redis** | Short-term memory, SSE queues, agent tracker |
| SQL DB | **PostgreSQL** | Users, documents, meetings, eval results |
| Web search | **DuckDuckGo** | Free, no API key |
| Speech-to-text | **faster-whisper** | Local Whisper inference |
| Text-to-speech | **edge-tts** | Microsoft Edge TTS, free, no key |
| Browser automation | **Playwright** | Headless Chromium for browser agent |
| Metrics | **Prometheus** + **Grafana** | Request metrics + dashboards |
| Tracing | **OpenTelemetry** + **Jaeger** | Distributed traces (optional) |
| LLM tracing | **LangSmith** | Optional run tracing (free tier) |

### Frontend

| Technology | Purpose |
|-----------|---------|
| **React 18** + **Vite** + **TypeScript** | SPA framework |
| **Tailwind CSS** | Utility-first styling |
| **React Router v6** | Client-side routing |
| **Zustand** | Auth state management |
| **Lucide React** | Icon library |
| **Axios** | HTTP client (base API) |
| Native `fetch` + **SSE** | Streaming responses |
| Native **WebSocket** | Real-time agent status + voice |
| **Web Audio API** | TTS playback, silence detection |
| **MediaRecorder API** | Audio capture for voice |

---

## Folder Structure

```
multi_agent_ai/
│
├── .env.example                    # All env vars documented — copy to .env
├── .env                            # Local secrets (not committed)
├── .gitignore
├── IMPLEMENTATION.md               # Phase-by-phase implementation blueprint
├── docker-compose.yml              # Full local stack (8 infrastructure services)
├── docker-compose.observability.yml# Prometheus + Grafana + Jaeger
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint → typecheck → build → Docker images
│       └── deploy.yml              # Railway (backend) + Vercel (frontend) on push to main
│
├── deployment/
│   ├── railway.toml                # Railway backend deployment config
│   ├── vercel.json                 # Vercel frontend deployment config
│   └── README.md                   # Step-by-step deployment instructions
│
├── observability/
│   ├── prometheus.yml              # Scrape config targeting backend:8000/metrics
│   └── grafana/
│       ├── provisioning/           # Auto-loaded datasource + dashboard providers
│       └── dashboards/ai_os.json   # Pre-built request rate/latency/error dashboard
│
├── docs/
│   └── PROJECT_GUIDE.md            # This file
│
├── backend/
│   ├── Dockerfile                  # Python 3.11-slim + Playwright Chromium
│   ├── entrypoint.sh               # alembic upgrade head → uvicorn start
│   ├── requirements.txt            # 28 Python packages
│   ├── start_dev.sh                # Local dev without Docker
│   ├── alembic.ini
│   ├── alembic/versions/
│   │   ├── 001_initial.py          # users, refresh_tokens tables
│   │   ├── 002_documents.py        # documents, document_chunks tables
│   │   ├── 003_meetings.py         # meetings table
│   │   └── 004_eval_results.py     # eval_results table
│   │
│   └── app/
│       ├── main.py                 # FastAPI app — lifespan, middleware, router registration
│       ├── config.py               # Pydantic Settings — all env vars with defaults
│       ├── database.py             # Connection factories for PG, Redis, Qdrant, Neo4j, ES
│       │
│       ├── models/                 # SQLAlchemy ORM models (PostgreSQL)
│       │   ├── user.py             # User, RefreshToken
│       │   ├── document.py         # Document, DocumentChunk
│       │   ├── meeting.py          # Meeting (with JSONB fields for analysis)
│       │   └── eval_result.py      # EvalResult (metric scores per run)
│       │
│       ├── schemas/
│       │   └── auth.py             # RegisterRequest, LoginRequest, TokenResponse
│       │
│       ├── routers/                # FastAPI route handlers
│       │   ├── auth.py             # POST /api/auth/register, /login, /refresh, /me
│       │   ├── chat.py             # POST /api/chat/stream (SSE — multi-agent)
│       │   ├── documents.py        # GET/POST/DELETE /api/documents/
│       │   ├── retrieval.py        # POST /api/retrieval/explain, /search
│       │   ├── memory.py           # GET /api/memory/{history,episodes,summary,search,stats,clear}
│       │   ├── graph.py            # GET/POST /api/graph/{stats,entities,relationships,search,ingest}
│       │   ├── meetings.py         # GET/POST/DELETE /api/meetings/, POST /{id}/jira, GET /blockers
│       │   ├── browser.py          # GET /api/browser/templates, POST /run (SSE)
│       │   ├── eval.py             # GET /api/eval/{stats,runs,agent-stats}, POST /score, /run
│       │   ├── ws.py               # WS /ws/{client_id} — live agent status push
│       │   └── voice_ws.py         # WS /ws/voice — full-duplex voice AI
│       │
│       ├── agents/                 # LangGraph multi-agent pipeline
│       │   ├── state.py            # AgentState TypedDict (shared across all nodes)
│       │   ├── nodes.py            # Five node functions + _emit() SSE helper
│       │   └── graph.py            # StateGraph wiring + conditional retry edges
│       │
│       └── services/
│           ├── rag.py              # Base RAG: Qdrant search → Ollama stream
│           ├── document.py         # PDF → chunks → Qdrant + ES + Neo4j
│           ├── auth.py             # JWT creation, password hashing, token validation
│           │
│           ├── retrieval/          # Adaptive Retrieval Engine (Phase 4)
│           │   ├── classifier.py   # LLM picks strategy: vector|keyword|graph|web
│           │   ├── vector.py       # Qdrant cosine similarity
│           │   ├── keyword.py      # Elasticsearch BM25
│           │   ├── graph.py        # Delegates to graph_rag_search()
│           │   ├── web.py          # DuckDuckGo async search
│           │   ├── merger.py       # Weighted merge (vector:1.0, graph:0.9, keyword:0.85, web:0.75)
│           │   └── router.py       # adaptive_retrieve() — fan-out + merge
│           │
│           ├── memory/             # Layered Memory System (Phase 5)
│           │   ├── decay.py        # score = 0.7×similarity + 0.3×exp(−age_days×ln2/7)
│           │   ├── short_term.py   # Redis list — last 20 conversation turns
│           │   ├── episodic.py     # Redis sorted set — 30-day rolling episodes
│           │   ├── semantic.py     # Qdrant memory_vectors collection — embedded Q&A pairs
│           │   ├── summary.py      # LLM compression at 15-turn threshold
│           │   └── manager.py      # retrieve_context() + save() unified API
│           │
│           ├── knowledge_graph/    # Knowledge Graph (Phase 6)
│           │   ├── schema.py       # 6 node labels, 5 relationship types, constraint DDL
│           │   ├── extractor.py    # LLM extracts entities/relationships from text
│           │   ├── ingestion.py    # MERGE-based Neo4j upsert + relationship weight counter
│           │   ├── cypher_gen.py   # NL → Cypher (with write-op safety guard regex)
│           │   └── searcher.py     # graph_rag_search(), get_entity_stats(), get_relationships()
│           │
│           ├── meeting/            # Meeting Intelligence (Phase 7)
│           │   ├── transcription.py# faster-whisper — shared model singleton
│           │   ├── diarization.py  # Gap-based speaker assignment (>0.5s gap → new speaker)
│           │   ├── analysis.py     # LLM extracts topics/actions/decisions/blockers as JSON
│           │   ├── jira.py         # Jira REST v3 (or simulated if unconfigured)
│           │   └── pipeline.py     # Orchestrates: transcribe→diarize→analyse→graph→memory→DB
│           │
│           ├── browser/            # Browser Agent (Phase 8)
│           │   ├── session.py      # Playwright isolated Chromium context manager
│           │   ├── actions.py      # navigate/search/click/fill/scroll_down/done + URL guard
│           │   ├── extractor.py    # LLM extracts structured JSON from page text
│           │   ├── navigator.py    # LLM decision loop (max 12 steps) + SSE events per step
│           │   └── reporter.py     # Markdown report generator + 4 built-in templates
│           │
│           ├── voice/              # Voice AI (Phase 9)
│           │   ├── stt.py          # faster-whisper bytes → transcript
│           │   ├── tts.py          # edge-tts MP3 chunk streaming (en-US-AriaNeural)
│           │   ├── tone.py         # LLM emotion classifier (6 labels)
│           │   └── agent_bridge.py # rag_stream() adapter for low-latency voice responses
│           │
│           └── eval/               # Evaluation & Observability (Phase 10)
│               ├── metrics.py      # LLM-as-judge: faithfulness, answer_relevancy, context_precision
│               ├── agent_tracker.py# Redis counters: per-agent success/failure/latency
│               ├── benchmark.py    # Batch eval runner → Postgres storage
│               ├── langsmith_tracer.py # Optional LangSmith run posting
│               └── otel_setup.py   # OpenTelemetry FastAPI instrumentation
│
└── frontend/
    ├── Dockerfile                  # Multi-stage: Node 20 build → Nginx 1.27 serve
    ├── nginx.conf                  # SPA fallback + /api/ proxy + WebSocket upgrade
    ├── vite.config.ts              # Dev proxy: /api/ → :8000, /ws/ → ws://:8000
    │
    └── src/
        ├── App.tsx                 # React Router — 10 protected routes
        ├── main.tsx                # React entry point
        │
        ├── pages/
        │   ├── Login.tsx           # JWT login form
        │   ├── Dashboard.tsx       # Chat + AgentPanel + floating VoiceOrb
        │   ├── Agents.tsx          # Pipeline diagram reference page
        │   ├── Documents.tsx       # PDF upload, list, delete
        │   ├── Memory.tsx          # Memory stats, history, episodes, semantic search
        │   ├── KnowledgeGraph.tsx  # Entity/relationship browser + NL→Cypher search
        │   ├── Voice.tsx           # Meeting upload + transcript + analysis tabs
        │   ├── Browser.tsx         # Browser agent — templates + live step feed + report
        │   ├── Eval.tsx            # RAG metrics + agent success rates + benchmark runner
        │   └── Settings.tsx        # Account info + clear all memory
        │
        ├── components/
        │   ├── layout/
        │   │   ├── Sidebar.tsx     # Nav with 10 items
        │   │   └── Header.tsx      # Page title + WS connection indicator
        │   ├── chat/
        │   │   └── ChatWindow.tsx  # Message list + streaming token display + input bar
        │   ├── agents/
        │   │   └── AgentPanel.tsx  # 5 agent status badges + retrieval trace display
        │   ├── retrieval/
        │   │   └── RetrievalBadge.tsx # Colored strategy badges (vector/keyword/graph/web)
        │   └── voice/
        │       └── VoiceOrb.tsx    # Animated mic button — state-aware ring animations
        │
        ├── hooks/
        │   ├── useAuth.ts          # Login/logout + token refresh
        │   ├── useWebSocket.ts     # WS with exponential backoff reconnect (5 retries)
        │   └── useVoiceSession.ts  # MediaRecorder + silence detection + AudioContext TTS
        │
        ├── services/               # Typed API clients
        │   ├── api.ts              # Axios base instance
        │   ├── ragApi.ts           # streamAgent() async generator — consumes SSE
        │   ├── browserApi.ts       # runTask() async generator — consumes SSE
        │   ├── meetingsApi.ts      # Meetings CRUD + Jira
        │   ├── graphApi.ts         # Graph stats/entities/search
        │   ├── memoryApi.ts        # Memory history/search/clear
        │   └── evalApi.ts          # Eval stats/score/benchmark
        │
        ├── store/
        │   └── authStore.ts        # Zustand store — JWT tokens with localStorage persistence
        └── types/
            └── index.ts            # Shared TS interfaces (Message, AgentStatus, etc.)
```

---

## Architecture Overview

```
Browser (React SPA)
    │
    │  HTTP / SSE / WebSocket
    ▼
FastAPI (port 8000)
    │
    ├── /api/auth/*         → PostgreSQL (JWT)
    ├── /api/chat/stream    → LangGraph Agent Pipeline
    │       ├── Planner     → Ollama llama3.1
    │       ├── Researcher  → Adaptive Retrieval
    │       │       ├── Vector  → Qdrant
    │       │       ├── Keyword → Elasticsearch
    │       │       ├── Graph   → Neo4j
    │       │       └── Web     → DuckDuckGo
    │       ├── Executor    → Ollama llama3.1 (streaming)
    │       ├── Critic      → Ollama llama3.1 (quality gate, max 2 retries)
    │       └── Memory      → Redis + Qdrant + Ollama (all 4 layers)
    ├── /api/documents/*    → PyPDF → Qdrant + Elasticsearch + Neo4j
    ├── /api/memory/*       → Redis + Qdrant
    ├── /api/graph/*        → Neo4j
    ├── /api/meetings/*     → faster-whisper + Ollama + PostgreSQL
    ├── /api/browser/*      → Playwright (headless Chromium) + Ollama
    ├── /api/eval/*         → Ollama (LLM-as-judge) + Redis + PostgreSQL
    ├── /ws/{client_id}     → Redis pub-sub → live agent status
    └── /ws/voice           → faster-whisper + Ollama + edge-tts (WebSocket)
```

---

## Component Workflows

### 1. Authentication

```
POST /api/auth/register
  → validate email + username → bcrypt hash password → INSERT users → return user

POST /api/auth/login
  → lookup user by email → verify bcrypt hash
  → generate access_token (HS256, 30min) + refresh_token (7 days)
  → return {access_token, refresh_token, token_type}

POST /api/auth/refresh
  → verify refresh_token → generate new access_token

All protected endpoints:
  → extract Bearer token from Authorization header
  → decode JWT → get user_id → validate expiry
```

**Frontend:** Zustand `authStore` persists both tokens to `localStorage`. The `useAuth` hook handles login/logout and the `ProtectedRoute` wrapper in `App.tsx` redirects unauthenticated requests to `/login`.

---

### 2. Document Ingestion

```
POST /api/documents/upload (multipart form, PDF file)
  │
  ├─ 1. Save file to backend/uploads/
  ├─ 2. Extract text from PDF (pypdf)
  ├─ 3. Split into ~500-char overlapping chunks
  ├─ 4. For each chunk:
  │       ├─ Embed with nomic-embed-text via Ollama → store in Qdrant (collection: documents)
  │       ├─ Index in Elasticsearch (BM25 index: document_chunks)
  │       └─ Extract entities/relationships via LLM → MERGE into Neo4j
  │            (first 5 chunks only, wrapped in try/except)
  └─ 5. INSERT document record in PostgreSQL
       → return document metadata
```

**Key files:** `services/document.py`, `services/knowledge_graph/extractor.py`, `services/knowledge_graph/ingestion.py`

---

### 3. Multi-Agent Chat

The chat pipeline uses a **LangGraph StateGraph** with 5 nodes and conditional retry edges:

```
POST /api/chat/stream
  → create request_id → create asyncio.Queue in status_queues dict
  → run agent_graph in background task
  → stream SSE events from queue to client

Agent pipeline (LangGraph):

  START
    │
  [Planner]
    ├─ Retrieves memory context (recent history + semantic + summary)
    ├─ LLM breaks query into 2-3 subtasks
    └─ Emits: agent_status(running→done)
    │
  [Researcher]
    ├─ Calls adaptive_retrieve(query) — see section 4
    ├─ Emits: retrieval_trace event (strategies used + result counts)
    └─ Emits: agent_status(running→done)
    │
  [Executor]
    ├─ Builds prompt: query + subtasks + retrieved context + memory preamble
    ├─ Streams llama3.1 response token-by-token
    ├─ Emits: stream_start → chat_token(×N) → stream_end
    └─ Emits: agent_status(running→done)
    │
  [Critic]
    ├─ LLM evaluates: {"is_acceptable": bool, "critique": str}
    └─ Emits: agent_status(running→done)
    │
  [Conditional edge]
    ├─ If acceptable OR iteration ≥ 2 → [Memory]
    └─ Else → [Executor] (retry with critique injected)
    │
  [Memory]
    ├─ Saves to all 4 memory layers (short_term, episodic, semantic, summary)
    ├─ Emits: memory_saved event
    ├─ Emits: agent_status(running→done)
    └─ Puts None sentinel → SSE generator exits
    │
  END
```

**SSE event types received by frontend:**

| Event type | Payload | Action |
|-----------|---------|--------|
| `agent_status` | `{agent, status, message}` | Update agent badge color |
| `retrieval_trace` | `{strategies_used, source_counts}` | Show retrieval badges |
| `stream_start` | `{}` | Prepare message slot |
| `chat_token` | `{token}` | Append token to message |
| `stream_end` | `{}` | Mark streaming complete |
| `memory_saved` | `{short_term_entries, compressed}` | (logged) |
| `error` | `{message}` | Show error in chat |

**Key files:** `agents/graph.py`, `agents/nodes.py`, `agents/state.py`, `routers/chat.py`

---

### 4. Adaptive Retrieval Engine

```
adaptive_retrieve(query)
  │
  ├─ 1. Classify query intent (Ollama LLM)
  │       → picks 1-2 strategies from: vector | keyword | graph | web
  │       → returns: {strategies: [...], reasoning: "..."}
  │
  ├─ 2. Fan out concurrently (asyncio.gather):
  │       ├─ vector:  Qdrant cosine similarity (top-5, embed query first)
  │       ├─ keyword: Elasticsearch BM25 (top-5, document_chunks index)
  │       ├─ graph:   Neo4j NL→Cypher search (LLM generates Cypher, safety guard blocks writes)
  │       └─ web:     DuckDuckGo search (top-3 results, run in thread executor)
  │
  └─ 3. Merge and re-rank (merger.py):
          ├─ Normalize scores within each source
          ├─ Apply source weights: vector×1.0, graph×0.9, keyword×0.85, web×0.75
          ├─ Add temporal boost: web results get +0.08
          ├─ Deduplicate (skip if first 120 chars match an existing result)
          └─ Return top-8 results with source labels
```

**Key files:** `services/retrieval/router.py`, `services/retrieval/classifier.py`, `services/retrieval/merger.py`

---

### 5. Layered Memory System

Four independent memory layers, all written on every agent turn:

```
retrieve_context(query)
  ├─ short_term:  Redis LIST "memory:short_term" → last 20 Q&A turns
  ├─ episodic:    Redis ZSET "memory:episodes" → entries scored by unix timestamp
  ├─ semantic:    Qdrant "memory_vectors" → top-3 by composite score:
  │                   score = 0.7 × cosine_similarity + 0.3 × recency_decay
  │                   recency_decay = exp(−age_days × ln2 / 7)   ← half-life = 7 days
  └─ summary:     Redis STRING "memory:summary" → LLM-compressed conversation summary

save(query, response)
  ├─ short_term:  RPUSH + LTRIM to 20
  ├─ episodic:    ZADD with current unix timestamp as score
  ├─ semantic:    Embed Q+A pair → Qdrant upsert into memory_vectors
  └─ summary:     If short_term length ≥ 15 → compress last N turns via LLM,
                  keep last 5 raw turns, store compressed in Redis
```

The retrieved context is injected into the Executor node prompt as three labeled sections:
- `[Memory Summary]` — compressed historical context
- `[Relevant Past Conversations]` — semantic matches
- `[Recent History]` — last 3 raw turns

**Key files:** `services/memory/manager.py`, `services/memory/decay.py`, `services/memory/semantic.py`

---

### 6. Knowledge Graph

**Graph schema (Neo4j):**

| Node labels | Properties |
|------------|-----------|
| Person | name, title, email |
| Organization | name, domain, industry |
| Project | name, status, deadline |
| Topic | name, category |
| Concept | name, definition |
| Document | title, source_id |

| Relationship types |
|-------------------|
| WORKS_AT |
| LEADS |
| PART_OF |
| RELATED_TO |
| MENTIONS |

```
Document upload pipeline:
  chunk text → LLM extraction → {"entities": [...], "relationships": [...]}
  → validate labels/types → MERGE nodes with timestamps
  → MERGE relationships with weight counter (increments on duplicate)
  → Link Document node → Entity via MENTIONS edges

NL→Cypher search (GET /api/graph/search?q=...):
  → LLM generates Cypher from natural language
  → Safety guard: regex blocks CREATE/DELETE/SET/MERGE/DROP
  → Execute read-only Cypher → return nodes + relationships + generated query
```

**Key files:** `services/knowledge_graph/extractor.py`, `services/knowledge_graph/ingestion.py`, `services/knowledge_graph/cypher_gen.py`, `services/knowledge_graph/searcher.py`

---

### 7. Meeting Intelligence

```
POST /api/meetings/upload (audio file: mp3/wav/m4a/webm)
  │
  ├─ 1. Save audio file
  ├─ 2. Transcribe (faster-whisper, lazy singleton model load)
  │       → returns: transcript text + [{start, end, text}] segments + duration + language
  ├─ 3. Diarize (gap-based speaker assignment)
  │       → speaker changes when gap between segments > 0.5s
  │       → merge consecutive same-speaker turns
  │       → returns: [{speaker, text, start, end}]
  ├─ 4. Analyse (single LLM call)
  │       → extracts: topics, action_items, decisions, blockers as validated JSON
  ├─ 5. Ingest into Knowledge Graph (entities from transcript)
  ├─ 6. Save Q&A summary to Memory system
  ├─ 7. Cache blockers/decisions in Redis (for /api/meetings/blockers endpoint)
  └─ 8. UPDATE meeting record in PostgreSQL with all results

POST /api/meetings/{id}/jira
  → Create Jira issues for each action item
  → If JIRA_BASE_URL not configured: return simulated issue keys (PROJ-XXX)
```

**Key files:** `services/meeting/pipeline.py`, `services/meeting/transcription.py`, `services/meeting/diarization.py`, `services/meeting/analysis.py`

---

### 8. Browser Agent

```
POST /api/browser/run {"task": "..."}
  │
  ├─ Create asyncio.Queue → start SSE stream
  ├─ Launch isolated Playwright Chromium context (headless)
  │
  └─ LLM action loop (max 12 steps):
       ├─ Get current page state (URL + cleaned inner_text, max 3000 chars)
       ├─ LLM decides next action from: navigate|search|click|fill|scroll_down|extract|done
       ├─ Execute action (URL safety guard: blocks private IPs, non-http schemes)
       ├─ Emit SSE: step_start → (execute) → step_done
       ├─ On "extract" action: LLM parses page → structured JSON → emit "extracted" event
       ├─ On "done" action: exit loop
       └─ 0.5s polite delay between steps

→ generate_report(task, steps, extractions) via Ollama
→ Emit SSE: report event with full Markdown content
→ Close browser context
```

**Built-in templates:** AI Startup Hiring Report, GitHub Trending Repos, Hacker News Top Stories, Product Hunt Top Products

**Key files:** `services/browser/navigator.py`, `services/browser/actions.py`, `services/browser/extractor.py`, `services/browser/reporter.py`

---

### 9. Voice AI

Full-duplex WebSocket at `/ws/voice`. State machine: `idle → listening → processing → speaking`.

```
Client → Server messages:
  {type: "audio_chunk", data: "<base64 webm/opus>", is_last: bool}
  {type: "barge_in"}   ← interrupts TTS mid-stream
  {type: "ping"}

Server → Client messages:
  {type: "state",       state: "idle|listening|processing|speaking"}
  {type: "transcript",  text: "what the user said"}
  {type: "tone",        tone: "neutral|positive|frustrated|confused|excited|concerned"}
  {type: "agent_token", token: "response word"}
  {type: "tts_chunk",   data: "<base64 mp3>"}
  {type: "tts_done"}

Flow:
  audio_chunk (is_last=false) → accumulate bytes, emit state=listening
  audio_chunk (is_last=true)  → concat bytes → faster-whisper transcript
                              → emit transcript
                              → tone detection (parallel, Ollama)
                              → stream rag_stream() response token by token
                              → emit tone result
                              → edge-tts synthesise MP3 chunks → emit tts_chunk×N → tts_done
  barge_in → cancel TTS task → emit state=listening
```

**Frontend `useVoiceSession` hook:**
- `MediaRecorder` captures WebM/Opus audio
- `AnalyserNode` detects silence (avg frequency < 8) → auto-stops after 1.5s
- `AudioContext.decodeAudioData` plays back MP3 TTS chunks
- Barge-in: sends `{type: "barge_in"}` and clears TTS buffer

**Key files:** `routers/voice_ws.py`, `services/voice/stt.py`, `services/voice/tts.py`, `services/voice/tone.py`, `frontend/src/hooks/useVoiceSession.ts`

---

### 10. Evaluation & Observability

**LLM-as-judge metrics** (RAGAS-equivalent, computed via Ollama locally):

| Metric | Definition | Good threshold |
|--------|-----------|---------------|
| `faithfulness` | Are all answer claims supported by the context? | ≥ 0.75 |
| `answer_relevancy` | Does the answer address the question? | ≥ 0.70 |
| `context_precision` | Are retrieved chunks relevant to the question? | ≥ 0.65 |
| `hallucination_score` | 1 − faithfulness (lower is better) | < 0.25 |

**Agent success tracking** (Redis counters, 30-day TTL):
- Every LangGraph node calls `record_success(agent_name, elapsed_ms)` on completion
- Counters: `eval:agent:{name}:{successes|failures|total_ms|calls}`
- Available at `GET /api/eval/agent-stats`

**Prometheus metrics** (`/metrics` endpoint):
- Request count by endpoint + status code
- Request latency histograms (p50/p95/p99)
- Scraped by Prometheus; displayed in Grafana pre-built dashboard

**Optional integrations:**
- **LangSmith**: set `LANGSMITH_API_KEY` → run traces posted to `https://api.smith.langchain.com`
- **OpenTelemetry/Jaeger**: set `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`

---

## API Reference

All endpoints are prefixed with `/api/`. Auth endpoints are public; all others require `Authorization: Bearer <token>`.

### Auth — `/api/auth`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/register` | `{username, email, password}` | User object |
| POST | `/login` | `{email, password}` | `{access_token, refresh_token}` |
| POST | `/refresh` | `{refresh_token}` | `{access_token}` |
| GET | `/me` | — | Current user |

### Documents — `/api/documents`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | List of documents |
| POST | `/upload` | multipart `file` (PDF) | Document metadata |
| DELETE | `/{id}` | — | `{deleted: true}` |

### Chat — `/api/chat`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/stream` | `{query, request_id?}` | SSE stream of events |

### Retrieval — `/api/retrieval`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| POST | `/explain` | `{query}` | `{strategies, reasoning}` |
| POST | `/search` | `{query, limit?}` | `{results, strategies_used}` |

### Memory — `/api/memory`

| Method | Path | Returns |
|--------|------|---------|
| GET | `/history` | Last 20 turns |
| GET | `/episodes` | Recent episodes |
| GET | `/summary` | Compressed summary |
| POST | `/search` | Semantic search results |
| GET | `/stats` | `{short_term_turns, episodic_events, vector_memories, has_summary}` |
| DELETE | `/clear` | `{cleared: true}` |

### Knowledge Graph — `/api/graph`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/stats` | — | Node counts by label |
| GET | `/entities` | `?type=&limit=` | Entity list |
| GET | `/relationships` | `?limit=` | Relationship list with weights |
| POST | `/search` | `{query}` | `{results, cypher}` |
| POST | `/ingest` | `{text}` | `{entities_added, relationships_added}` |

### Meetings — `/api/meetings`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/` | — | Meeting list |
| POST | `/upload` | multipart `file` (audio) | `{id, status: "processing"}` |
| GET | `/{id}` | — | Full meeting with analysis |
| DELETE | `/{id}` | — | `{deleted: true}` |
| POST | `/{id}/jira` | — | `{issues_created: [...]}` |
| GET | `/blockers` | — | Recent blockers from Redis |

### Browser — `/api/browser`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/templates` | — | `{templates: [...]}` |
| POST | `/run` | `{task}` | SSE stream of step/extracted/report events |

### Evaluation — `/api/eval`

| Method | Path | Body | Returns |
|--------|------|------|---------|
| GET | `/stats` | — | `{metrics: {...}, agents: [...]}` |
| GET | `/runs` | — | `{runs: [...], total}` |
| GET | `/agent-stats` | — | `{agents: [...]}` |
| POST | `/score` | `{query, response, contexts?}` | Per-metric scores + reasoning |
| POST | `/run` | `{cases?}` | `{run_id, status: "started"}` |

### WebSocket — `/ws`

| Path | Protocol | Purpose |
|------|---------|---------|
| `/ws/{client_id}` | WS | Receives agent status push events |
| `/ws/voice` | WS | Full-duplex voice AI (see section 9) |

### System

| Method | Path | Returns |
|--------|------|---------|
| GET | `/health` | `{status: "ok", service, version}` |
| GET | `/metrics` | Prometheus text format |
| GET | `/docs` | Swagger UI |

---

## Frontend Pages

| Route | Page | Key features |
|-------|------|-------------|
| `/` | Dashboard | Chat with multi-agent system, live agent status panel, floating voice orb |
| `/agents` | Agents | Pipeline diagram, node descriptions, tech stack reference |
| `/browser` | Browser Agent | Template picker, custom task input, live step feed, extracted data, downloadable report |
| `/documents` | Documents | PDF upload with drag-drop, document list, delete |
| `/graph` | Knowledge Graph | Entity browser (filterable by type), relationship table, NL Cypher search tab |
| `/memory` | Memory | Stats cards, compressed summary, tabbed: Recent History / Episodes / Semantic Search |
| `/voice` | Voice (Meetings) | Audio upload, transcript view, speaker diarization, topics/actions/decisions/blockers tabs, Jira export |
| `/eval` | Evaluation | RAG quality metric cards, agent success table, benchmark runner, on-demand score form, run history |
| `/settings` | Settings | Account info, stack reference, clear all memory button |
| `/login` | Login | Email + password form |

---

## Running the Project

### Prerequisites

- **Python 3.11+** with `venv`
- **Node.js 20+**
- **Docker** (for infrastructure services)
- **Ollama** installed locally ([install guide](https://ollama.com))

### Option A — Local Dev (recommended for development)

This runs the backend and frontend directly on your machine with hot-reload. Docker only runs the infrastructure services.

**Step 1 — Start infrastructure services**

```bash
# From project root
docker compose up -d postgres redis qdrant neo4j elasticsearch
```

Wait ~30 seconds for services to initialize, then verify:
```bash
docker compose ps
# All should show "healthy" or "running"
```

**Step 2 — Pull Ollama models** *(first time only — llama3.1 is ~4.7 GB)*

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

**Step 3 — Set up Python environment** *(first time only)*

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Install Playwright browsers (for browser agent)
.venv/bin/playwright install chromium
```

**Step 4 — Run database migrations** *(first time, and after any schema change)*

```bash
cd backend
POSTGRES_URL="postgresql+asyncpg://aiplatform:aiplatform@localhost:5432/aiplatform" \
  .venv/bin/alembic upgrade head
```

**Step 5 — Start the backend**

```bash
cd backend
POSTGRES_URL="postgresql+asyncpg://aiplatform:aiplatform@localhost:5432/aiplatform" \
REDIS_URL="redis://localhost:6379" \
QDRANT_HOST="localhost" QDRANT_PORT="6333" \
NEO4J_URI="bolt://localhost:7687" NEO4J_USER="neo4j" NEO4J_PASSWORD="aiplatform123" \
ELASTICSEARCH_URL="http://localhost:9200" \
OLLAMA_HOST="localhost" OLLAMA_PORT="11434" \
SECRET_KEY="dev-secret-key-change-in-production" \
CORS_ORIGINS='["http://localhost:5173"]' \
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the provided script:
```bash
cd backend
./start_dev.sh
```

Backend is available at: **http://localhost:8000**  
API docs (Swagger UI): **http://localhost:8000/docs**

**Step 6 — Start the frontend**

```bash
cd frontend
npm install        # first time only
npm run dev
```

Frontend is available at: **http://localhost:5173**

**Step 7 — Create your first user**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@demo.com","password":"admin123"}'
```

Then open **http://localhost:5173** and log in.

---

### Option B — Full Docker Compose

Builds and runs everything (including backend and frontend) in containers. No local Python or Node.js needed.

```bash
# Step 1 — copy and configure env
cp .env.example .env
# Edit .env — at minimum change SECRET_KEY to a random value

# Step 2 — build and start all services (first run takes 10–15 min)
docker compose up -d --build

# Step 3 — pull Ollama models inside the container (first time only)
docker compose exec ollama ollama pull llama3.1
docker compose exec ollama ollama pull nomic-embed-text

# Step 4 — create your first user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@demo.com","password":"admin123"}'
```

App is available at **http://localhost** (port 80, served by Nginx).

**Start the observability stack (optional):**

```bash
docker compose -f docker-compose.observability.yml up -d

# Grafana dashboard: http://localhost:3001  (admin / admin)
# Prometheus:        http://localhost:9090
# Jaeger traces:     http://localhost:16686
# Enable OTel:       set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 in .env
```

**Useful Docker commands:**

```bash
# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Restart a single service after code changes
docker compose up -d --build backend

# Stop everything
docker compose down

# Stop and remove all volumes (full reset)
docker compose down -v
```

---

## Environment Variables

All variables are optional with sensible defaults for local dev. Copy `.env.example` to `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key-...` | **Change in production.** JWT signing key |
| `POSTGRES_URL` | `postgresql+asyncpg://aiplatform:aiplatform@localhost:5432/aiplatform` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `aiplatform123` | Neo4j password |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | Elasticsearch URL |
| `OLLAMA_HOST` | `localhost` | Ollama host |
| `OLLAMA_PORT` | `11434` | Ollama port |
| `WHISPER_MODEL` | `base` | Whisper model size (`tiny`/`base`/`small`/`medium`/`large`) |
| `JIRA_BASE_URL` | *(empty)* | Jira instance URL — simulated if unset |
| `JIRA_USERNAME` | *(empty)* | Jira username/email |
| `JIRA_API_TOKEN` | *(empty)* | Jira API token |
| `LANGSMITH_API_KEY` | *(empty)* | LangSmith API key — tracing disabled if unset |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | *(empty)* | OTLP gRPC endpoint — console spans if unset |
| `PROMETHEUS_ENABLED` | `true` | Expose `/metrics` endpoint |
| `VITE_API_URL` | *(empty = relative)* | Frontend API base URL (set for external backend) |
| `VITE_WS_URL` | *(empty = same host)* | Frontend WebSocket base URL |

---

## Database Migrations

Migrations are in `backend/alembic/versions/`. Alembic is configured to use `POSTGRES_URL` from the environment.

```bash
# Apply all pending migrations
cd backend
POSTGRES_URL="..." .venv/bin/alembic upgrade head

# Check current migration version
POSTGRES_URL="..." .venv/bin/alembic current

# Rollback one migration
POSTGRES_URL="..." .venv/bin/alembic downgrade -1

# Generate a new migration after model changes
POSTGRES_URL="..." .venv/bin/alembic revision --autogenerate -m "describe_change"
```

| Migration | Tables created |
|-----------|---------------|
| `001_initial` | `users`, `refresh_tokens` |
| `002_documents` | `documents`, `document_chunks` |
| `003_meetings` | `meetings` (with JSONB columns for analysis output) |
| `004_eval_results` | `eval_results` (metric scores per benchmark run) |

---

## Deployment

See [`deployment/README.md`](../deployment/README.md) for full instructions on:

- **Option A**: Local Docker Compose (all services on one machine)
- **Option B**: Railway (backend) + Vercel (frontend) — live public URL

**Quick Railway deploy:**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link
railway login
cd backend
railway up
```

Set these environment variables in the Railway dashboard:
- `SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
- `POSTGRES_URL` (provided by Railway PostgreSQL add-on)
- `REDIS_URL` (provided by Railway Redis add-on)
- All other vars pointing to your cloud-hosted services

**Quick Vercel deploy (frontend):**

```bash
# Install Vercel CLI
npm install -g vercel

cd frontend
vercel
# Set VITE_API_URL=https://your-railway-backend.up.railway.app
# Set VITE_WS_URL=wss://your-railway-backend.up.railway.app
```

---

*Built across 11 phases: Base RAG → Multi-Agent → Adaptive Retrieval → Layered Memory → Knowledge Graph → Meeting Intelligence → Browser Agent → Voice AI → Evaluation & Observability → Deployment & CI/CD.*
