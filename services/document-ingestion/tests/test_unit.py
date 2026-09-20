import pytest

from app.security import sha256_bytes, validate_filename, validate_extension
from app.extractors import extract_text
from app.chunker import chunk_document
from app.models import DocumentMetadata, NormalizedDocument


def test_hash_deterministic():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abcd")


def test_filename_and_extension():
    assert validate_filename("../test.md") == "test.md"
    assert validate_extension("test.md", {".md"}) == ".md"


def test_markdown_extraction():
    blocks = extract_text("test.md", b"# Заглавие\n\nТекст за документа.")
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
