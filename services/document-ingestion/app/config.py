from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "document-ingestion"
    version: str = "0.3.0"
    host: str = "0.0.0.0"
    port: int = 8095
    max_file_size_mb: int = 1024
    knowledge_engine_url: str = "http://corporate-ai-knowledge-engine-0.3.1-test:8090"
    knowledge_engine_token: str = ""
    metadata_database_url: str = "postgresql://corporate_ai:corporate_ai@corporate-ai-postgres:5432/corporate_ai"
    repository_storage_path: str = "/data/repository"
    staging_storage_path: str = "/data/incoming"
    upload_chunk_size_bytes: int = 1024 * 1024
    ingest_timeout_seconds: float = 60.0
    vision_base_url: str = "http://corporate-ai-qwen36:8000/v1"
    vision_model: str = "qwen36"
    vision_timeout_seconds: float = 120.0
    vision_render_dpi: int = 150
    vision_min_native_text_chars: int = 20
    allowed_extensions: str = ".txt,.md,.markdown,.csv,.docx,.xls,.xlsx,.pptx,.pdf"
    paperless_webhook_secret: str = ""
    recovery_token: str = ""

    model_config = SettingsConfigDict(env_prefix="INGESTION_", extra="ignore")

    @property
    def allowed_suffixes(self) -> set[str]:
        return {x.strip().lower() for x in self.allowed_extensions.split(",") if x.strip()}


settings = Settings()
