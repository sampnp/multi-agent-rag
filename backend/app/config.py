from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise AI OS"
    DEBUG: bool = True

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    POSTGRES_URL: str = "postgresql+asyncpg://aiplatform:aiplatform@localhost:5432/aiplatform"
    REDIS_URL: str = "redis://localhost:6379"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "aiplatform123"

    ELASTICSEARCH_URL: str = "http://localhost:9200"

    OLLAMA_HOST: str = "localhost"
    OLLAMA_PORT: int = 11434

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    WHISPER_MODEL: str = "base"

    JIRA_BASE_URL: str = ""
    JIRA_USERNAME: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT_KEY: str = "PROJ"

    # Observability (all optional — no-ops if unset)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "enterprise-ai-os"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""  # e.g. http://localhost:4317
    PROMETHEUS_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
