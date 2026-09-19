import httpx
from .config import settings
from .models import Chunk

class KnowledgeEngineClient:
    def __init__(self, base_url: str | None=None):
        self.base_url=(base_url or settings.knowledge_engine_url).rstrip("/")

    async def ingest(self, chunk: Chunk) -> dict:
        payload={
            "document_id":chunk.document_id,
            "source_file":chunk.source_file,
            "content":chunk.content,
            "page":chunk.page,
            "page_type":chunk.page_type,
            "chunk_type":chunk.chunk_type,
            "section":chunk.section,
            "confidence":chunk.confidence,
        }
        async with httpx.AsyncClient(timeout=settings.ingest_timeout_seconds) as client:
            r=await client.post(f"{self.base_url}/v1/ingest", json=payload)
            r.raise_for_status()
            return r.json()

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r=await client.get(f"{self.base_url}/health")
                return r.is_success
        except Exception:
            return False
