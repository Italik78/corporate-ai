import pytest
from app.security import sha256_bytes, validate_filename, validate_extension
from app.extractors import extract_text
from app.chunker import chunk_document
from app.models import DocumentMetadata, NormalizedDocument

def test_hash_deterministic():
    assert sha256_bytes(b"abc")==sha256_bytes(b"abc")
    assert sha256_bytes(b"abc")!=sha256_bytes(b"abcd")

def test_filename_and_extension():
    assert validate_filename("../test.md")=="test.md"
    assert validate_extension("test.md",{".md"})==".md"

def test_markdown_extraction():
    blocks=extract_text("test.md",b"# Заглавие\n\nТекст за документа.")
    assert len(blocks)==2
    assert blocks[0].block_type=="heading"
    assert blocks[1].section=="Заглавие"

def test_chunking():
    blocks=extract_text("test.txt",("думата "*400).encode())
    meta=DocumentMetadata(document_id="d1",title="t",created_at="now",updated_at="now")
    doc=NormalizedDocument(document_id="d1",source_file="test.txt",media_type="text/plain",
        content_hash="x",metadata=meta,blocks=blocks)
    chunks=chunk_document(doc,target_words=100,overlap_words=10)
    assert len(chunks)>=4
    assert all(c.document_id=="d1" for c in chunks)
