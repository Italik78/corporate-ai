from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    service_name: str = "document-ingestion"
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8095
    max_file_size_mb: int = 25
    knowledge_engine_url: str = "http://corporate-ai-knowledge-engine-0.3.1-test:8090"
    ingest_timeout_seconds: float = 60.0
    allowed_extensions: str = ".txt,.md,.markdown"

    model_config = SettingsConfigDict(env_prefix="INGESTION_", extra="ignore")

    @property
    def allowed_suffixes(self) -> set[str]:
        return {x.strip().lower() for x in self.allowed_extensions.split(",") if x.strip()}

settings = Settings()
