import asyncio
import csv
import io

import pytest

from app.security import sha256_bytes, validate_filename, validate_extension
from app.extractors import extract_document, extract_text
from app.chunker import chunk_document
from app.models import DocumentMetadata, DocumentProcessResponse, IngestResponse, DocumentStatus, LifecycleStatus, NormalizedDocument
from app import pipeline


def test_hash_deterministic():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abcd")


def test_filename_and_extension():
    assert validate_filename("../test.md") == "test.md"
    assert validate_extension("test.md", {".md"}) == ".md"


def test_markdown_extraction():
    blocks = extract_text("test.md", "# Заглавие\n\nТекст за документа.".encode("utf-8"))
    assert len(blocks) == 2
    assert blocks[0].block_type == "heading"
    assert blocks[1].section == "Заглавие"


def _document(text: bytes) -> NormalizedDocument:
    blocks = extract_text("test.txt", text)
    meta = DocumentMetadata(
        document_id="d1",
        title="t",
        created_at="now",
        updated_at="now",
    )
    return NormalizedDocument(
        document_id="d1",
        source_file="test.txt",
        media_type="text/plain",
        content_hash="x",
        metadata=meta,
        blocks=blocks,
    )


def test_chunking():
    chunks = chunk_document(_document(("думата " * 400).encode()), target_words=100, overlap_words=10)
    assert len(chunks) >= 4
    assert all(c.document_id == "d1" for c in chunks)
    assert all(len(c.content.split()) <= 100 for c in chunks)


def test_chunking_preserves_real_overlap():
    chunks = chunk_document(
        _document((" ".join(f"w{i}" for i in range(120))).encode()),
        target_words=50,
        overlap_words=10,
    )
    assert len(chunks) == 3
    assert chunks[0].content.split()[-10:] == chunks[1].content.split()[:10]
    assert chunks[1].content.split()[-10:] == chunks[2].content.split()[:10]


def test_large_single_block_is_bounded():
    chunks = chunk_document(
        _document((" ".join(f"w{i}" for i in range(250))).encode()),
        target_words=80,
        overlap_words=10,
    )
    assert all(len(c.content.split()) <= 80 for c in chunks)
    assert len(chunks) >= 4


def test_chunk_provenance_is_present():
    chunks = chunk_document(
        _document(b"alpha beta gamma " * 100),
        target_words=40,
        overlap_words=5,
    )
    for chunk in chunks:
        assert chunk.provenance["content_hash"] == "x"
        assert chunk.provenance["block_ids"]
        assert chunk.provenance["first_block"]
        assert chunk.provenance["last_block"]


def test_invalid_chunk_parameters():
    doc = _document(b"alpha beta")
    with pytest.raises(ValueError):
        chunk_document(doc, target_words=0)
    with pytest.raises(ValueError):
        chunk_document(doc, target_words=10, overlap_words=10)


def test_document_metadata_version_foundation():
    metadata = DocumentMetadata(
        document_id="policy-001",
        title="Policy",
        created_at="2026-09-20T00:00:00+00:00",
        updated_at="2026-09-20T00:00:00+00:00",
        version=2,
        document_date="2026-09-20",
        effective_from="2026-10-01",
        project_id="project-001",
        access_scope="INTERNAL",
    )
    assert metadata.version == 2
    assert metadata.document_date == "2026-09-20"
    assert metadata.effective_from == "2026-10-01"
    assert metadata.lifecycle_status.value == "INGESTING"


def test_chunk_id_includes_version():
    doc = _document(b"alpha beta gamma")
    doc.metadata.version = 2
    chunks = chunk_document(doc)
    assert chunks[0].chunk_id == "d1:v2:chunk:00001"


def test_chunk_carries_version_metadata():
    doc = _document(b"alpha beta gamma")
    doc.metadata.version = 2
    doc.metadata.document_date = "2026-09-20"
    doc.metadata.effective_from = "2026-10-01"
    chunks = chunk_document(doc)
    assert chunks[0].document_id == "d1"
    assert chunks[0].version == 2
    assert chunks[0].document_date == "2026-09-20"
    assert chunks[0].effective_from == "2026-10-01"
    assert chunks[0].lifecycle_status.value == "INGESTING"
    assert chunks[0].content


def test_csv_extraction():
    data = "Име;Количество;Цена\nЛаптоп;2;1500\nМонитор;3;500\n".encode()
    blocks = extract_document("items.csv", data)
    assert len(blocks) == 1
    assert blocks[0].block_type == "table"
    assert "Име | Количество | Цена" in blocks[0].content
    assert "Лаптоп | 2 | 1500" in blocks[0].content
    assert blocks[0].provenance["source_format"] == "csv"


def test_docx_extraction():
    from docx import Document

    buffer = io.BytesIO()
    document = Document()
    document.add_heading("Командировки", level=1)
    document.add_paragraph("Дневните командировъчни са 40 EUR.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Разход"
    table.cell(0, 1).text = "Лимит"
    table.cell(1, 0).text = "Хотел"
    table.cell(1, 1).text = "100 EUR"
    document.save(buffer)

    blocks = extract_document("policy.docx", buffer.getvalue())
    assert len(blocks) == 3
    assert blocks[0].block_type == "heading"
    assert blocks[1].section == "Командировки"
    assert blocks[2].block_type == "table"
    assert "Разход | Лимит" in blocks[2].content
    assert blocks[2].provenance["source_format"] == "docx"


def test_stage_upload_preserves_original_extension(tmp_path, monkeypatch):
    class FakeUpload:
        filename = "test.xlsx"

        def __init__(self, data):
            self.data = io.BytesIO(data)

        async def read(self, size):
            return self.data.read(size)

    monkeypatch.setattr(pipeline.settings, "staging_storage_path", str(tmp_path))
    monkeypatch.setattr(pipeline.settings, "upload_chunk_size_bytes", 1024)
    monkeypatch.setattr(pipeline.settings, "max_file_size_mb", 1)

    payload = b"fake-xlsx-content"
    staged_path, content_hash, total = asyncio.run(
        pipeline._stage_upload(FakeUpload(payload))
    )

    assert staged_path.suffix == ".xlsx"
    assert staged_path.name.startswith(".ingest-")
    assert staged_path.read_bytes() == payload
    assert total == len(payload)
    assert content_hash == sha256_bytes(payload)

    staged_path.unlink()

def test_xlsx_extraction():
    from openpyxl import Workbook

    buffer = io.BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Бюджет"
    worksheet.append(["Артикул", "Количество", "Цена"])
    worksheet.append(["Лаптоп", 2, 1500])
    worksheet.append(["Монитор", 3, 500])
    workbook.save(buffer)

    blocks = extract_document("budget.xlsx", buffer.getvalue())
    assert len(blocks) == 1
    assert blocks[0].block_type == "table"
    assert blocks[0].section == "Бюджет"
    assert "Лаптоп | 2 | 1500" in blocks[0].content
    assert blocks[0].provenance["sheet"] == "Бюджет"


def test_pptx_extraction():
    from pptx import Presentation

    buffer = io.BytesIO()
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    title = slide.shapes.title
    title.text = "Проект"
    textbox = slide.shapes.add_textbox(1000000, 1000000, 5000000, 1000000)
    textbox.text = "Бюджетът е 100 000 EUR."
    table = slide.shapes.add_table(2, 2, 1000000, 2500000, 5000000, 2000000).table
    table.cell(0, 0).text = "Разход"
    table.cell(0, 1).text = "Сума"
    table.cell(1, 0).text = "Хардуер"
    table.cell(1, 1).text = "50 000 EUR"

    presentation.save(buffer)
    blocks = extract_document("brief.pptx", buffer.getvalue())
    assert len(blocks) == 3
    assert blocks[0].block_type == "heading"
    assert blocks[1].page == 1
    assert blocks[2].block_type == "table"
    assert "Хардуер | 50 000 EUR" in blocks[2].content
    assert blocks[2].provenance["slide"] == 1


def test_pdf_extraction():
    import fitz

    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Corporate AI PDF test")
    data = pdf.tobytes()
    pdf.close()

    blocks = extract_document("test.pdf", data)

    assert len(blocks) == 1
    assert blocks[0].block_type == "text"
    assert blocks[0].page == 1
    assert blocks[0].content == "Corporate AI PDF test"
    assert blocks[0].provenance["source_format"] == "pdf"
    assert blocks[0].provenance["page"] == 1
    assert blocks[0].provenance["extraction"] == "pymupdf_text"
    assert len(blocks[0].provenance["bbox"]) == 4


def test_unsupported_extractor():
    with pytest.raises(ValueError, match="UNSUPPORTED_FILE_TYPE"):
        extract_document("image.png", b"data")


def test_pipeline_repository_knowledge_critical_path(monkeypatch):
    calls = []

    class FakeRepository:
        async def register_version(self, metadata, source_file, content_hash):
            calls.append(("register", metadata.document_id, source_file))
            metadata.version = 1
            return metadata

        async def store_canonical_source(
            self, document_id, version, filename, data, content_hash
        ):
            calls.append(("store", document_id, version, filename))
            return f"documents/{document_id}/original/{version}/{filename}"

        async def set_canonical_storage_key(
            self, document_id, version, canonical_storage_key
        ):
            calls.append(("set_key", document_id, version, canonical_storage_key))

        async def finalize_version(self, document_id, version):
            calls.append(("finalize", document_id, version))
            return DocumentMetadata(
                document_id=document_id,
                title="critical-path",
                created_at="now",
                updated_at="now",
                version=version,
                lifecycle_status=LifecycleStatus.CURRENT,
            )

        async def fail_version(self, document_id, version):
            calls.append(("fail", document_id, version))

        async def delete_canonical_source(self, document_id, version, filename):
            calls.append(("delete", document_id, version, filename))

    class FakeKnowledgeClient:
        async def ingest(self, chunk):
            calls.append(("index", chunk.document_id, chunk.version))

        async def set_lifecycle_status(self, document_id, version, lifecycle_status):
            calls.append(("lifecycle", document_id, version, lifecycle_status))
            return {"status": "ok"}

    async def fake_create_ingestion_job(**kwargs):
        return None

    async def fake_update_ingestion_job(ingestion_id, **kwargs):
        return None

    async def fake_get_ingestion_job(ingestion_id):
        return None

    monkeypatch.setattr(pipeline, "create_ingestion_job", fake_create_ingestion_job)
    monkeypatch.setattr(pipeline, "update_ingestion_job", fake_update_ingestion_job)
    monkeypatch.setattr(pipeline, "get_ingestion_job", fake_get_ingestion_job)
    async def fake_find_duplicate_version(**kwargs):
        return None

    monkeypatch.setattr(pipeline, "find_duplicate_version", fake_find_duplicate_version)
    monkeypatch.setattr(pipeline, "repository", FakeRepository())
    monkeypatch.setattr(pipeline, "KnowledgeEngineClient", FakeKnowledgeClient)

    result = asyncio.run(
        pipeline.ingest_document(
            filename="critical-path.txt",
            data=b"Repository critical path",
            document_id="critical-path-001",
        )
    )

    assert result.status.value == "READY"
    assert result.lifecycle_status.value == "CURRENT"
    assert result.chunk_count == 1
    assert result.indexed_count == 1
    assert calls == [
        ("register", "critical-path-001", "critical-path.txt"),
        ("store", "critical-path-001", 1, "critical-path.txt"),
        (
            "set_key",
            "critical-path-001",
            1,
            "documents/critical-path-001/original/1/critical-path.txt",
        ),
        ("index", "critical-path-001", 1),
        ("finalize", "critical-path-001", 1),
        ("lifecycle", "critical-path-001", 1, "CURRENT"),
    ]

    document = asyncio.run(
        pipeline.ingest_document(
            filename="loader-path.txt",
            data=b"Repository loader path",
            document_id="loader-path-001",
            return_document=True,
        )
    )

    assert isinstance(document, DocumentProcessResponse)
    assert document.ingestion_id
    assert isinstance(document.document, NormalizedDocument)
    assert document.document.document_id == "loader-path-001"
    assert document.document.blocks[0].content == "Repository loader path"


def test_duplicate_process_reconstructs_document_from_index(monkeypatch):
    duplicate = type(
        "Duplicate",
        (),
        {
            "document_id": "existing-001",
            "source_system": "upload",
            "source_reference": None,
            "source_file": "existing.txt",
            "title": "Existing",
            "author": "Author",
            "classification": "INTERNAL",
            "created_at": "2026-09-20T00:00:00+00:00",
            "updated_at": "2026-09-20T00:00:00+00:00",
            "tags": ["test"],
            "language": "bg",
            "version": 2,
            "document_date": "2026-09-20",
            "effective_from": "2026-09-20",
            "effective_to": None,
            "lifecycle_status": LifecycleStatus.CURRENT,
            "parent_document_id": None,
            "supersedes": "existing-001:v1",
            "superseded_by": None,
            "project_id": "project-001",
            "access_scope": "INTERNAL",
            "canonical_storage_key": None,
            "content_hash": "same-hash",
        },
    )()

    class FakeKnowledgeClient:
        async def get_document_chunks(self, document_id, version):
            assert document_id == "existing-001"
            assert version == 2
            return [
                {
                    "chunk_id": "existing-001:v2:chunk:00002",
                    "chunk_type": "text",
                    "content": "Втори блок.",
                    "page": 2,
                    "section": "Секция 2",
                    "confidence": 0.91,
                    "provenance": {"block_ids": ["block-2"]},
                },
                {
                    "chunk_id": "existing-001:v2:chunk:00001",
                    "chunk_type": "text",
                    "content": "Първи блок.",
                    "page": 1,
                    "section": "Секция 1",
                    "confidence": 0.97,
                    "provenance": {"block_ids": ["block-1"]},
                },
            ]

    async def fake_create_ingestion_job(**kwargs):
        return None

    async def fake_update_ingestion_job(ingestion_id, **kwargs):
        return None

    async def fake_find_duplicate_version(**kwargs):
        return duplicate

    monkeypatch.setattr(pipeline, "create_ingestion_job", fake_create_ingestion_job)
    monkeypatch.setattr(pipeline, "update_ingestion_job", fake_update_ingestion_job)
    monkeypatch.setattr(pipeline, "find_duplicate_version", fake_find_duplicate_version)
    monkeypatch.setattr(pipeline, "KnowledgeEngineClient", FakeKnowledgeClient)

    result = asyncio.run(
        pipeline.ingest_document(
            filename="incoming.txt",
            data=b"same content",
            document_id="new-request-001",
            return_document=True,
        )
    )

    assert isinstance(result, DocumentProcessResponse)
    assert result.document.document_id == "existing-001"
    assert result.document.metadata.version == 2
    assert result.document.source_file == "existing.txt"
    assert result.document.content_hash == "same-hash"
    assert [block.content for block in result.document.blocks] == [
        "Първи блок.",
        "Втори блок.",
    ]
    assert result.document.blocks[0].provenance == {"block_ids": ["block-1"]}
    assert result.document.blocks[1].confidence == 0.91

    ingest_result = asyncio.run(
        pipeline.ingest_document(
            filename="incoming.txt",
            data=b"same content",
            document_id="new-request-002",
        )
    )

    assert isinstance(ingest_result, IngestResponse)
    assert ingest_result.document_id == "existing-001"
    assert ingest_result.version == 2
    assert ingest_result.status == DocumentStatus.READY
    assert ingest_result.chunk_count == 2
    assert ingest_result.indexed_count == 2
    assert ingest_result.page_count is None
    assert "DUPLICATE_CONTENT_REUSED" in ingest_result.warnings


def test_vision_json_validation():
    from app.vision import _extract_json, VisionError

    result = _extract_json(
        '{"page_type":"TEXT","title":null,"text":"Здравей","tables":[],'
        '"key_values":[],"entities":[],"visual_elements":[],'
        '"uncertain_items":[],"confidence":0.95}'
    )

    assert result["text"] == "Здравей"
    assert result["confidence"] == 0.95


def test_vision_rejects_invalid_json():
    from app.vision import _extract_json, VisionError

    with pytest.raises(VisionError, match="PDF_VISION_INVALID_JSON"):
        _extract_json("това не е JSON")


def test_vision_rejects_incomplete_schema():
    from app.vision import _extract_json, VisionError

    with pytest.raises(VisionError, match="PDF_VISION_INVALID_SCHEMA"):
        _extract_json('{"page_type":"TEXT","text":"test"}')


def test_vision_result_to_blocks_preserves_text_and_table():
    from app.pipeline import _vision_result_to_blocks

    blocks = _vision_result_to_blocks(
        {
            "_page": 3,
            "page_type": "COMPLEX",
            "title": "Отчет",
            "text": "Обща стойност: 123.45 EUR",
            "tables": [
                {
                    "headers": ["Артикул", "Количество"],
                    "rows": [["Лаптоп", 5]],
                }
            ],
            "key_values": [],
            "entities": [],
            "visual_elements": [],
            "uncertain_items": ["Една стойност е нечетлива"],
            "confidence": 0.91,
        },
        "scan.pdf",
    )

    assert len(blocks) == 2

    table = next(block for block in blocks if block.block_type == "table")
    text = next(block for block in blocks if block.block_type == "text")

    assert table.page == 3
    assert "Артикул | Количество" in table.content
    assert "Лаптоп | 5" in table.content
    assert text.content.startswith("Отчет")
    assert "123.45 EUR" in text.content
    assert text.confidence == 0.91
    assert text.provenance["extraction"] == "qwen3_6_vision"
    assert text.provenance["uncertain_items"] == ["Една стойност е нечетлива"]
