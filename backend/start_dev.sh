#!/bin/bash
# Run this from the backend/ directory: ./start_dev.sh
export POSTGRES_URL="postgresql+asyncpg://aiplatform:aiplatform@localhost:5432/aiplatform"
export REDIS_URL="redis://localhost:6379"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_PASSWORD="aiplatform123"
export ELASTICSEARCH_URL="http://localhost:9200"
export SECRET_KEY="dev-secret-key-change-in-production"

echo "Running migrations..."
.venv/bin/alembic upgrade head

echo "Starting backend on http://localhost:8000"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
