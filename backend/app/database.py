from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient
from neo4j import AsyncGraphDatabase
from elasticsearch import AsyncElasticsearch
from typing import AsyncGenerator

from app.config import settings


class Base(DeclarativeBase):
    pass


# PostgreSQL
engine = create_async_engine(settings.POSTGRES_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Redis
redis_client: aioredis.Redis | None = None


async def connect_redis():
    global redis_client
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def disconnect_redis():
    if redis_client:
        await redis_client.aclose()


# Qdrant
qdrant_client: AsyncQdrantClient | None = None


async def connect_qdrant():
    global qdrant_client
    qdrant_client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def disconnect_qdrant():
    if qdrant_client:
        await qdrant_client.close()


def get_qdrant() -> AsyncQdrantClient:
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialised")
    return qdrant_client


# Neo4j
neo4j_driver = None


async def connect_neo4j():
    global neo4j_driver
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )


async def disconnect_neo4j():
    if neo4j_driver:
        await neo4j_driver.close()


# Elasticsearch
es_client: AsyncElasticsearch | None = None


async def connect_elasticsearch():
    global es_client
    es_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)


async def disconnect_elasticsearch():
    if es_client:
        await es_client.close()
