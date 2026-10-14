from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_url: str = "http://localhost:6333"
    ollama_url: str = "http://localhost:11434"
    storage_path: str = "/data/documents"
    max_upload_bytes: int = 20 * 1024 * 1024
    embedding_model: str = "nomic-embed-text:latest"
    chat_model: str = "qwen2.5:0.5b"
    qdrant_collection: str = "localrag_chunks"
    top_k: int = 5
    session_ttl_seconds: int = 3600  # 1 hour of inactivity


@lru_cache
def get_settings() -> Settings:
    return Settings()
