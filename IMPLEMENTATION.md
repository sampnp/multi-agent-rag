# Enterprise AI Operating System — Implementation Tracker

> **Status legend:** `[ ]` = not started · `[~]` = in progress · `[x]` = done · `[!]` = blocked

---

## Project Overview

**Goal:** Build a production-grade, modular multi-agent AI platform — not a chatbot.  
**Stack summary:** React.js (Vite) · FastAPI · LangGraph · Ollama + Groq (LiteLLM router) · Qdrant · Neo4j · Elasticsearch · Redis Streams · faster-whisper · Coqui TTS · Playwright + Browser-use · RAGAS + DeepEval · Docker Compose → Railway

---

## Phases

### PHASE 1 — Foundation
**Goal:** Get the skeleton running end-to-end with auth, websocket, and databases.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | Initialize monorepo folder structure | [x] | |
| 1.2 | Setup Docker Compose (dev environment) | [x] | All 6 services: postgres, redis, qdrant, neo4j, elasticsearch, backend, frontend |
| 1.3 | Setup React.js frontend (TypeScript + Tailwind + Vite) | [x] | Login, Dashboard, ChatWindow, Sidebar, Header |
| 1.4 | Setup FastAPI backend with health check | [x] | GET /health, lifespan startup/shutdown |
| 1.5 | WebSocket connection (frontend ↔ backend) | [x] | Auto-reconnect with exponential backoff |
| 1.6 | JWT authentication (login / refresh / logout) | [x] | Access + refresh tokens, token rotation |
| 1.7 | Configure PostgreSQL (users, sessions) | [x] | Alembic migrations, users + refresh_tokens tables |
| 1.8 | Configure Redis (caching + pub-sub) | [x] | Connection wired, ready for use in Phase 3+ |
| 1.9 | Configure Qdrant (vector DB) | [x] | Connection wired, ready for use in Phase 2 |
| 1.10 | Configure Neo4j (graph DB) | [x] | Connection wired, ready for use in Phase 6 |
| 1.11 | Basic CI pipeline (GitHub Actions) | [x] | Lint + type check + Docker build |

---

### PHASE 2 — Base RAG
**Goal:** Ingest documents and answer questions from them.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 2.1 | PDF upload API endpoint | [x] | POST /api/documents/upload, 50MB limit, background processing |
| 2.2 | Document chunking service (recursive + semantic) | [x] | 800 char chunks, 100 overlap |
| 2.3 | Embedding generation (OpenAI / local) | [x] | nomic-embed-text via Ollama (768-dim, free) |
| 2.4 | Store embeddings in Qdrant | [x] | "documents" collection, cosine similarity |
| 2.5 | Vector similarity search | [x] | Top-5 chunk retrieval |
| 2.6 | Context injection into LLM prompt | [x] | Numbered sources injected into system prompt |
| 2.7 | Basic Q&A endpoint (RAG pipeline) | [x] | POST /api/chat/rag — SSE streaming via llama3.1 |
| 2.8 | Frontend: document upload + chat UI | [x] | Documents page (drag & drop), Dashboard streams RAG responses |

---

### PHASE 3 — Multi-Agent System
**Goal:** Replace single LLM calls with an orchestrated agent graph.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 3.1 | Setup LangGraph orchestration scaffold | [x] | StateGraph with conditional edges; agents/graph.py + state.py |
| 3.2 | Research Agent (retrieval + memory search) | [x] | Qdrant vector search, top-5 chunks |
| 3.3 | Planning Agent (task decomposition) | [x] | LLM breaks query into 2-3 subtasks (JSON output) |
| 3.4 | Execution Agent (tool calling + workflows) | [x] | Streams tokens via Ollama; emits chat_token SSE events |
| 3.5 | Critic Agent (hallucination detection) | [x] | Evaluates quality; routes back to executor if not acceptable (max 2 retries) |
| 3.6 | Memory Agent (store + retrieve long-term memory) | [x] | Stores Q&A pair in Redis (7-day TTL) |
| 3.7 | Agent communication protocol (shared state schema) | [x] | AgentState TypedDict; asyncio.Queue per request for SSE events |
| 3.8 | Agent execution trace logging | [x] | agent_status SSE events (running/done/error + message) streamed live |
| 3.9 | Frontend: agent activity panel (live updates) | [x] | AgentPanel.tsx; streamAgent() async generator; Dashboard updated |

---

### PHASE 4 — Adaptive Retrieval Engine
**Goal:** Route each query to the best retrieval strategy automatically.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 4.1 | Query classifier (LLM-based routing logic) | [x] | LLM picks from vector/keyword/graph/web; services/retrieval/classifier.py |
| 4.2 | Vector retrieval path | [x] | Wraps existing Qdrant search_documents; services/retrieval/vector.py |
| 4.3 | Graph retrieval path (Neo4j Cypher queries) | [x] | Keyword-to-Cypher; gracefully empty until Phase 6 populates graph |
| 4.4 | Keyword / BM25 retrieval path (Elasticsearch) | [x] | ES index "document_chunks"; chunks auto-indexed on upload |
| 4.5 | Live web search path (SerpAPI / Tavily) | [x] | DuckDuckGo (free, no API key) via duckduckgo-search; services/retrieval/web.py |
| 4.6 | Retrieval result merging + re-ranking | [x] | Per-source score normalisation + source weights + dedup; merger.py |
| 4.7 | Temporal relevance scoring | [x] | Web results boosted +0.08 for freshness in merger |
| 4.8 | Retrieval strategy explainability log | [x] | retrieval_trace SSE event; RetrievalBadge in AgentPanel; /api/retrieval/explain endpoint |

---

### PHASE 5 — Memory System
**Goal:** Give agents persistent, layered memory across sessions.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 5.1 | Short-term memory (in-context window) | [x] | Redis list, last 20 turns; injected into Executor prompt |
| 5.2 | Conversation summary memory (LLM compression) | [x] | llama3.1 compresses older turns into bullet-point summary; Redis key |
| 5.3 | Episodic memory (event-based storage) | [x] | Redis sorted set scored by unix timestamp; 30-day TTL |
| 5.4 | Semantic memory (concepts + relationships) | [x] | Q&A pairs embedded + stored in Qdrant memory_vectors collection |
| 5.5 | Vector memory (embedding-based retrieval) | [x] | nomic-embed-text; semantic.search() retrieves top-3 similar past Q&A |
| 5.6 | Memory compression pipeline | [x] | Triggers at 15 turns: LLM summarises older entries, list trimmed to 5 |
| 5.7 | Memory read/write API | [x] | /api/memory/{history,episodes,summary,search,stats,clear}; Memory page in UI |
| 5.8 | Memory decay / relevance scoring | [x] | Exponential decay (half-life 7 days); composite = 0.7×similarity + 0.3×recency |

---

### PHASE 6 — Knowledge Graph
**Goal:** Move from flat document retrieval to relationship-aware enterprise memory.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 6.1 | Entity extraction (spaCy / LLM-based) | [x] | llama3.1 extracts Person/Organization/Project/Topic/Concept; validated + sanitized |
| 6.2 | Relationship extraction pipeline | [x] | WORKS_ON, BELONGS_TO, MENTIONS, RELATES_TO, DEPENDS_ON; merged across chunks |
| 6.3 | Neo4j schema design (Person, Meeting, Project, Issue…) | [x] | 6 node labels, 5 rel types, MERGE-based dedup, uniqueness constraints |
| 6.4 | Graph ingestion from documents | [x] | First 5 chunks extracted on PDF upload; ingest() called in process_document |
| 6.5 | Temporal event tracking (timestamps on edges) | [x] | created_at on all nodes + relationships; weight counter on repeated co-mentions |
| 6.6 | Ownership + dependency graphs | [x] | BELONGS_TO (ownership) + DEPENDS_ON (dependency) relationships |
| 6.7 | Cypher query generation from natural language | [x] | cypher_gen.py: llama3.1 → Cypher; read-only safety guard (regex rejects writes) |
| 6.8 | Graph RAG retrieval integration | [x] | retrieval/graph.py delegates to graph_rag_search; NL→Cypher→results in retrieval pipeline |

---

### PHASE 7 — Meeting Intelligence
**Goal:** Turn meeting recordings into structured knowledge automatically.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 7.1 | Meeting audio upload endpoint | [x] | POST /api/meetings/upload; mp3/mp4/wav/m4a/webm; 200 MB limit |
| 7.2 | Whisper transcription service | [x] | faster-whisper (local, free); base model; runs in thread pool |
| 7.3 | Speaker diarization (pyannote.audio) | [x] | Silence-gap diarizer (no HF token needed); Speaker 1..N assignment + turn merging |
| 7.4 | Topic segmentation | [x] | LLM extracts 2–6 topics; displayed as badges |
| 7.5 | Action item extraction (LLM-based) | [x] | llama3.1 extracts task/owner/due/priority; displayed per meeting |
| 7.6 | Decision extraction | [x] | Decisions + blockers extracted; blocker cards in red |
| 7.7 | Jira task creation from action items | [x] | POST /api/meetings/{id}/jira; simulated if JIRA_BASE_URL not set |
| 7.8 | Update memory graph from meeting | [x] | Graph ingestion (entities from transcript) + episodic memory save |
| 7.9 | Unresolved decision + blocker tracking | [x] | Redis sorted sets meeting:decisions:unresolved + meeting:blockers:unresolved |
| 7.10 | Frontend: meeting upload + summary view | [x] | Voice page replaced — upload, list, transcript, speakers, actions, decisions tabs |

---

### PHASE 8 — Browser Agent
**Goal:** Allow agents to autonomously browse and extract information from the web.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 8.1 | Playwright browser session manager | [x] | Isolated browser context per task; headless Chromium; auto-cleanup |
| 8.2 | Browser-use / Stagehand integration | [x] | Custom LLM navigation loop (Playwright + Ollama) — same concept, no external deps |
| 8.3 | Autonomous navigation controller | [x] | navigator.py: llama3.1 decides next action from page state; max 12 steps |
| 8.4 | Form fill + click action executor | [x] | actions.py: navigate/search/click/fill/scroll; URL safety guard (blocks private IPs) |
| 8.5 | Structured data extractor from pages | [x] | extractor.py: LLM extracts structured JSON from inner_text; fallback raw excerpt |
| 8.6 | Report generation from browsing results | [x] | reporter.py: llama3.1 synthesises all extractions into markdown report; downloadable |
| 8.7 | Example workflow: AI startup hiring report | [x] | 4 pre-built templates: AI Hiring, GitHub Trending, HN Top Stories, Product Hunt |

---

### PHASE 9 — Voice AI
**Goal:** Support natural voice interaction with the platform.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 9.1 | Streaming speech-to-text (Whisper streaming) | [ ] | |
| 9.2 | WebRTC audio capture in frontend | [ ] | |
| 9.3 | Text-to-speech with ElevenLabs | [ ] | |
| 9.4 | Interruption / barge-in handling | [ ] | |
| 9.5 | Emotion / tone detection (optional) | [ ] | |
| 9.6 | Voice session state management | [ ] | |
| 9.7 | Frontend: voice interface component | [ ] | |

---

### PHASE 10 — Evaluation + Observability
**Goal:** Continuously measure quality, reliability, and performance.

| # | Task | Status | Notes |
|---|------|--------|-------|
| 10.1 | RAGAS evaluation integration | [ ] | |
| 10.2 | DeepEval test suite | [ ] | |
| 10.3 | TruLens feedback pipeline | [ ] | |
| 10.4 | Hallucination rate tracking | [ ] | |
| 10.5 | Faithfulness + context precision metrics | [ ] | |
| 10.6 | Agent success rate logging | [ ] | |
| 10.7 | OpenTelemetry tracing (all services) | [ ] | |
| 10.8 | Grafana dashboards (latency, errors, token usage) | [ ] | |
| 10.9 | LangSmith trace integration | [ ] | |
| 10.10 | Benchmark result storage (continuous) | [ ] | |

---

## Folder Structure

```
/
├── frontend/              # React.js app (Vite + TypeScript + Tailwind)
├── backend/               # FastAPI gateway + orchestrator
├── agents/                # Agent definitions (Research, Planning, etc.)
├── retrieval/             # Adaptive retrieval engine
├── memory/                # Memory layer services
├── knowledge_graph/       # Entity extraction + Neo4j integration
├── evals/                 # Evaluation pipelines (RAGAS, DeepEval)
├── observability/         # OTel, Grafana, LangSmith config
├── browser_agent/         # Playwright + browser automation
├── voice/                 # STT, TTS, WebRTC
├── workflows/             # Reusable workflow definitions
├── docs/                  # Architecture docs
├── benchmarks/            # Stored benchmark results
└── deployment/            # Docker, Kubernetes, Nginx, CI config
```

---

## Requirements & Change Log

> Record all requirement changes here so implementation decisions stay traceable.

| Date | Change | Impact |
|------|--------|--------|
| 2026-05-17 | Initial blueprint imported | All phases |
| 2026-05-17 | Replaced Next.js with React.js (Vite) | Phase 1.3, frontend folder, stack summary |
| 2026-05-17 | Locked all D1–D16 stack decisions: free-first, self-hosted, portfolio-optimized | All phases — see Decision Points table |

---

## Decision Points — Choose Your Stack

> Every row below has multiple valid options. Tell me your pick and I'll lock it in and update all relevant tasks.

| # | Decision | Chosen | Reason |
|---|----------|--------|--------|
| D1 | **Agent orchestration framework** | `LangGraph` | Most fine-grained control, best Python ecosystem fit, widely recognized on resumes |
| D2 | **Primary LLM** | `Ollama` (local) + `Groq` (free API) | Ollama runs Llama 3 / Mistral locally for free; Groq free tier gives fast cloud inference for demos — use `LiteLLM` to route between them |
| D3 | **Embedding model** | `nomic-embed-text` via Ollama | Completely free, runs locally, high quality, no API key needed |
| D4 | **Vector database** | `Qdrant` (self-hosted Docker) | Free, best Python SDK, most resume-worthy vector DB |
| D5 | **Keyword / BM25 search** | `Elasticsearch` (self-hosted Docker) | Free self-hosted, impressive on resume, standard in enterprise search |
| D6 | **Live web search** | `DuckDuckGo API` (free) + `Tavily` free tier | DuckDuckGo needs no key; Tavily free tier (1000 req/month) as fallback |
| D7 | **Message queue** | `Redis Streams` | Already in stack, simpler ops, sufficient for a portfolio project |
| D8 | **Entity extraction** | `spaCy` + LLM fallback (Ollama) | spaCy is fast and free; Ollama LLM fallback for complex entities — both free |
| D9 | **Browser automation** | `Playwright` + `Browser-use` | Playwright for low-level control; Browser-use for LLM-native browsing tasks |
| D10 | **Speech-to-text** | `Whisper` (local via `faster-whisper`) | 100% free, runs locally, good accuracy, no API key |
| D11 | **Text-to-speech** | `Coqui TTS` (local, free) | Fully open-source, no API key, decent quality; use ElevenLabs free tier (personal account) for demo recordings only |
| D12 | **Evaluation** | `RAGAS` + `DeepEval` | RAGAS for RAG-specific metrics, DeepEval for broader LLM eval — both open source |
| D13 | **Authentication** | `Custom JWT` | Free, no external service, shows backend engineering skill on resume |
| D14 | **DB hosting** | `Self-hosted Docker Compose` | Free, everything runs locally during development |
| D15 | **Deployment** | `Docker Compose` (local) → `Railway` free tier (demo) | Free local dev; Railway free tier for a live demo link on resume |
| D16 | **CI/CD** | `GitHub Actions` | Free tier is generous, industry standard |

---

## Open Questions

- [ ] Which Ollama models to use? (recommended: `llama3.2` for chat, `nomic-embed-text` for embeddings, `mistral` as fallback)
- [ ] Jira integration in Phase 7 — do you want this, or replace with a simpler task export (JSON / Notion)?
- [ ] Railway deployment — do you want a live public demo URL on your resume, or just local Docker is fine?
- [ ] GitHub repo name / visibility (public for resume visibility?)

---

## Current Focus

**Active phase:** Phase 3 — Multi-Agent System  
**Next action:** Begin Phase 3.1 — LangGraph orchestration scaffold

---

## Notes

- Build incrementally, phase by phase — do not skip ahead.
- Execution quality > feature count.
- Every architectural decision should be documented in the Change Log above.
