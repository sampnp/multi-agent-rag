from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import (
    connect_elasticsearch,
    connect_neo4j,
    connect_qdrant,
    connect_redis,
    disconnect_elasticsearch,
    disconnect_neo4j,
    disconnect_qdrant,
    disconnect_redis,
)
from app.routers import auth, ws, documents, chat, retrieval, memory, graph, meetings, browser, voice_ws, eval


import logging

logger = logging.getLogger(__name__)


async def _try_connect(name: str, coro):
    try:
        await coro
        logger.info("Connected to %s", name)
    except Exception as e:
        logger.warning("Could not connect to %s (will retry on use): %s", name, e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _try_connect("Redis", connect_redis())
    await _try_connect("Qdrant", connect_qdrant())
    await _try_connect("Neo4j", connect_neo4j())
    await _try_connect("Elasticsearch", connect_elasticsearch())
    yield
    await disconnect_redis()
    await disconnect_qdrant()
    await disconnect_neo4j()
    await disconnect_elasticsearch()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Enterprise AI Operating System API",
    lifespan=lifespan,
)

# Prometheus metrics endpoint (/metrics)
if settings.PROMETHEUS_ENABLED:
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app)
    except ImportError:
        logger.warning("prometheus-fastapi-instrumentator not installed — /metrics disabled")

# OpenTelemetry (no-op if packages missing or endpoint unset)
from app.services.eval.otel_setup import setup_otel
setup_otel(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(retrieval.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(meetings.router, prefix="/api")
app.include_router(browser.router, prefix="/api")
app.include_router(eval.router, prefix="/api")
app.include_router(ws.router)
app.include_router(voice_ws.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "backend", "version": "0.1.0"}
