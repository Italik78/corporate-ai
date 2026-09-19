from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from .config import settings
from .security import validate_filename, validate_size, validate_extension, sha256_bytes, security_scan
from .extractors import extract_text
from .chunker import chunk_document
from .models import DocumentMetadata, NormalizedDocument, IngestResponse, DocumentStatus
from .knowledge_client import KnowledgeEngineClient

jobs={}

def now():
    return datetime.now(timezone.utc).isoformat()

async def ingest_document(filename: str, data: bytes, document_id: str|None=None, source_system: str="upload") -> IngestResponse:
    ingestion_id=str(uuid4())
    document_id=document_id or str(uuid4())
    jobs[ingestion_id]={"document_id":document_id,"status":DocumentStatus.RECEIVED}
    try:
        filename=validate_filename(filename)
        validate_size(data, settings.max_file_size_mb*1024*1024)
        validate_extension(filename, settings.allowed_suffixes)
        jobs[ingestion_id]["status"]=DocumentStatus.SECURITY_CHECK
        warnings=security_scan(data)
        jobs[ingestion_id]["status"]=DocumentStatus.ROUTING
        jobs[ingestion_id]["status"]=DocumentStatus.EXTRACTING
        blocks=extract_text(filename,data)
        if not blocks:
            raise ValueError("EMPTY_DOCUMENT")
        content_hash=sha256_bytes(data)
        metadata=DocumentMetadata(
            document_id=document_id, source_system=source_system,
            title=Path(filename).stem, created_at=now(), updated_at=now())
        doc=NormalizedDocument(
            document_id=document_id, source_file=filename,
            media_type=_media_type(filename), content_hash=content_hash,
            metadata=metadata, blocks=blocks)
        jobs[ingestion_id]["status"]=DocumentStatus.NORMALIZING
        jobs[ingestion_id]["status"]=DocumentStatus.METADATA
        jobs[ingestion_id]["status"]=DocumentStatus.DEDUPLICATING
        jobs[ingestion_id]["status"]=DocumentStatus.CHUNKING
        chunks=chunk_document(doc)
        jobs[ingestion_id]["status"]=DocumentStatus.INDEXING
        client=KnowledgeEngineClient()
        indexed=0
        for chunk in chunks:
            await client.ingest(chunk)
            indexed+=1
        jobs[ingestion_id]["status"]=DocumentStatus.READY
        return IngestResponse(ingestion_id=ingestion_id,document_id=document_id,status=DocumentStatus.READY,
            content_hash=content_hash,chunk_count=len(chunks),indexed_count=indexed,warnings=warnings)
    except ValueError as e:
        code=str(e)
        status=DocumentStatus.FAILED_SECURITY if code in {"INVALID_FILENAME","FILE_TOO_LARGE","UNSUPPORTED_FILE_TYPE"} else DocumentStatus.FAILED_PARSING
        jobs[ingestion_id]={"document_id":document_id,"status":status,"error_code":code,"error":code}
        return IngestResponse(ingestion_id=ingestion_id,document_id=document_id,status=status,
            content_hash=sha256_bytes(data),chunk_count=0,indexed_count=0,error_code=code,error=code)
    except Exception as e:
        jobs[ingestion_id]={"document_id":document_id,"status":DocumentStatus.FAILED_INDEXING,"error_code":"INGESTION_ERROR","error":str(e)}
        return IngestResponse(ingestion_id=ingestion_id,document_id=document_id,status=DocumentStatus.FAILED_INDEXING,
            content_hash=sha256_bytes(data),chunk_count=0,indexed_count=0,error_code="INGESTION_ERROR",error=str(e))

def get_job(ingestion_id: str):
    return jobs.get(ingestion_id)

def _media_type(filename):
    return {
        ".txt":"text/plain",".md":"text/markdown",".markdown":"text/markdown"
    }.get(Path(filename).suffix.lower(),"application/octet-stream")
