"""Isolated ingestion-path acceptance for a scanned PDF.

This exercises the production pipeline stages with local Repository/KE fakes
and a deterministic Vision response. It proves routing and provenance wiring;
it does not replace DGX Vision/model and Qdrant end-to-end acceptance.
"""

import asyncio
import hashlib

import fitz

from app import pipeline
from app.models import DocumentMetadata, LifecycleStatus
from app.storage import FilesystemCanonicalStorage


class _Upload:
    filename = "scanned.pdf"

    def __init__(self, data: bytes):
        self._data = data
        self._read = False

    async def read(self, _size: int):
        if self._read:
            return b""
        self._read = True
        return self._data


def _blank_scanned_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=300, height=300)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 300, 300), False)
    pixmap.clear_with(255)
    page.insert_image(page.rect, stream=pixmap.tobytes("png"))
    pixmap = None
    result = document.tobytes()
    document.close()
    return result


def test_scanned_pdf_ingest_routes_vision_and_reaches_ready_current(
    monkeypatch, tmp_path
):
    pdf_bytes = _blank_scanned_pdf()
    storage = FilesystemCanonicalStorage(tmp_path / "repository")
    state = {}

    class FakeRepository:
        async def register_version(self, metadata, source_file, content_hash):
            metadata.version = 1
            state["metadata"] = metadata
            return metadata

        async def store_canonical_source_file(
            self, document_id, version, filename, source_path, content_hash
        ):
            return storage.store_file(
                document_id,
                version,
                filename,
                source_path,
                content_hash,
            )

        async def set_canonical_storage_key(
            self, document_id, version, canonical_storage_key
        ):
            state["key"] = canonical_storage_key

        async def inspect_version_integrity(self, document_id, version):
            from app.reconciliation import ReconciliationState, VersionIntegrity

            return VersionIntegrity(
                state=ReconciliationState.REPAIRABLE,
                document_id=document_id,
                version=version,
                lifecycle_status="INGESTING",
                canonical_storage_key=state["key"],
                reason="CANONICAL_SOURCE_VERIFIED_REPLAYABLE",
            )

        async def finalize_version(self, document_id, version):
            metadata = state["metadata"].model_copy(
                update={"lifecycle_status": LifecycleStatus.CURRENT}
            )
            return metadata

    class FakeKnowledgeClient:
        def __init__(self):
            self.chunks = []
            self.lifecycle = []

        async def ingest(self, chunk):
            assert chunk.canonical_source_verified is True
            assert chunk.canonical_storage_key == state["key"]
            self.chunks.append(chunk)

        async def set_lifecycle_status(self, **kwargs):
            self.lifecycle.append(kwargs)

    async def create_job(**kwargs):
        return None

    async def update_job(*args, **kwargs):
        return None

    async def find_duplicate(**kwargs):
        return None

    async def vision(path, native_blocks):
        assert path.suffix == ".pdf"
        assert native_blocks == []  # the generated scanned page has no native text
        pdf = fitz.open(str(path))
        try:
            assert pdf.page_count == 1
            assert pdf[0].get_images(full=True)
        finally:
            pdf.close()
        return [
            {
                "_page": 1,
                "page_type": "TABLE",
                "title": "Оферта",
                "text": "Обща цена: 125.00 EUR",
                "tables": [
                    {"headers": ["Услуга", "Цена"], "rows": [["X", "125.00 EUR"]]}
                ],
                "uncertain_items": [],
                "confidence": 0.98,
            }
        ]

    client = FakeKnowledgeClient()
    monkeypatch.setattr(pipeline, "create_ingestion_job", create_job)
    monkeypatch.setattr(pipeline, "update_ingestion_job", update_job)
    monkeypatch.setattr(pipeline, "find_duplicate_version", find_duplicate)
    monkeypatch.setattr(pipeline, "repository", FakeRepository())
    monkeypatch.setattr(pipeline, "KnowledgeEngineClient", lambda: client)
    monkeypatch.setattr(pipeline, "analyze_sparse_pdf_pages", vision)
    monkeypatch.setattr(
        pipeline.settings,
        "staging_storage_path",
        str(tmp_path / "staging"),
    )

    result = asyncio.run(
        pipeline.ingest_document(
            filename="scanned.pdf",
            upload=_Upload(pdf_bytes),
            document_id="scanned-pdf-test-001",
        )
    )

    assert result.status.value == "READY"
    assert result.lifecycle_status.value == "CURRENT"
    assert result.page_count == 1
    assert result.chunk_count == result.indexed_count == len(client.chunks)
    assert state["key"] == "documents/scanned-pdf-test-001/original/1/scanned.pdf"
    assert storage.verify_key(state["key"], hashlib.sha256(pdf_bytes).hexdigest()) == pdf_bytes
    assert any("125.00 EUR" in chunk.content for chunk in client.chunks)
    assert all(chunk.classification == "INTERNAL" for chunk in client.chunks)
    assert any(
        "qwen3_6_vision" in str(chunk.provenance)
        for chunk in client.chunks
    )
    assert client.lifecycle == [
        {
            "document_id": "scanned-pdf-test-001",
            "version": 1,
            "lifecycle_status": "CURRENT",
        }
    ]
