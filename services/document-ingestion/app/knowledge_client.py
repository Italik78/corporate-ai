import httpx

from .config import settings
from .models import Chunk


class KnowledgeEngineClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.knowledge_engine_url).rstrip("/")

    async def ingest(self, chunk: Chunk) -> dict:
        payload = {
            "document_id": chunk.document_id,
            "source_file": chunk.source_file,
            "version": chunk.version,
            "lifecycle_status": chunk.lifecycle_status.value,
            "document_date": chunk.document_date,
            "effective_from": chunk.effective_from,
            "effective_to": chunk.effective_to,
            "project_id": chunk.project_id,
            "access_scope": chunk.access_scope,
            "content": chunk.content,
            "page": chunk.page,
            "page_type": chunk.page_type,
            "chunk_type": chunk.chunk_type,
            "chunk_id": chunk.chunk_id,
            "section": chunk.section,
            "confidence": chunk.confidence,
        }
        async with httpx.AsyncClient(timeout=settings.ingest_timeout_seconds) as client:
            r = await client.post(f"{self.base_url}/v1/ingest", json=payload)
            r.raise_for_status()
            return r.json()

    async def set_lifecycle_status(
        self,
        document_id: str,
        version: int,
        lifecycle_status: str,
    ) -> dict:
        async with httpx.AsyncClient(timeout=settings.ingest_timeout_seconds) as client:
            r = await client.post(
                f"{self.base_url}/v1/documents/lifecycle",
                params={
                    "document_id": document_id,
                    "version": version,
                    "lifecycle_status": lifecycle_status,
                },
            )
            r.raise_for_status()
            return r.json()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/health")
                return r.is_success
        except Exception:
            return False
