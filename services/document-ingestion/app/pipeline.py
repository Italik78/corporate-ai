from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .chunker import chunk_document
from .config import settings
from .extractors import extract_document
from .knowledge_client import KnowledgeEngineClient
from .repository import (
    DuplicateDocumentError,
    VersionConflictError,
    repository,
)
from .models import (
    DocumentMetadata,
    DocumentStatus,
    IngestResponse,
    LifecycleStatus,
    NormalizedDocument,
)
from .security import (
    security_scan,
    sha256_bytes,
    validate_extension,
    validate_filename,
    validate_size,
)

jobs = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _media_type(filename: str) -> str:
    return {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".csv": "text/csv",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
    }.get(Path(filename).suffix.lower(), "application/octet-stream")


async def ingest_document(
    filename: str,
    data: bytes,
    document_id: str | None = None,
    source_system: str = "upload",
    version: int | None = None,
    document_date: str | None = None,
    effective_from: str | None = None,
    effective_to: str | None = None,
    project_id: str | None = None,
    access_scope: str = "INTERNAL",
    author: str | None = None,
    classification: str = "INTERNAL",
    tags: list[str] | None = None,
) -> IngestResponse:
    ingestion_id = str(uuid4())
    document_id = document_id or str(uuid4())
    requested_version = version or 1

    jobs[ingestion_id] = {
        "document_id": document_id,
        "version": requested_version,
        "status": DocumentStatus.RECEIVED,
    }

    content_hash = sha256_bytes(data)
    registered_version: int | None = None

    try:
        filename = validate_filename(filename)
        validate_size(data, settings.max_file_size_mb * 1024 * 1024)
        validate_extension(filename, settings.allowed_suffixes)

        jobs[ingestion_id]["status"] = DocumentStatus.SECURITY_CHECK
        warnings = security_scan(data, Path(filename).suffix.lower())

        jobs[ingestion_id]["status"] = DocumentStatus.ROUTING
        jobs[ingestion_id]["status"] = DocumentStatus.EXTRACTING
        blocks = extract_document(filename, data)
        if not blocks:
            raise ValueError("EMPTY_DOCUMENT")

        jobs[ingestion_id]["status"] = DocumentStatus.NORMALIZING
        metadata = DocumentMetadata(
            document_id=document_id,
            source_system=source_system,
            title=Path(filename).stem,
            author=author,
            classification=classification,
            created_at=now(),
            updated_at=now(),
            tags=tags or [],
            version=requested_version,
            document_date=document_date,
            effective_from=effective_from,
            effective_to=effective_to,
            project_id=project_id,
            access_scope=access_scope,
        )
        doc = NormalizedDocument(
            document_id=document_id,
            source_file=filename,
            media_type=_media_type(filename),
            content_hash=content_hash,
            metadata=metadata,
            blocks=blocks,
        )

        jobs[ingestion_id]["status"] = DocumentStatus.METADATA
        metadata = await repository.register_version(
            metadata=metadata,
            source_file=filename,
            content_hash=content_hash,
        )
        registered_version = metadata.version
        jobs[ingestion_id]["version"] = registered_version

        # register_version() may resolve an automatically assigned version and
        # populate supersedes metadata. Chunk IDs must use the resolved version,
        # not the initially requested version captured in the original document.
        doc.metadata = metadata

        jobs[ingestion_id]["status"] = DocumentStatus.DEDUPLICATING
        jobs[ingestion_id]["status"] = DocumentStatus.CHUNKING
        chunks = chunk_document(doc)

        for chunk in chunks:
            chunk.version = metadata.version
            chunk.lifecycle_status = LifecycleStatus.INGESTING
            chunk.document_date = metadata.document_date
            chunk.effective_from = metadata.effective_from
            chunk.effective_to = metadata.effective_to
            chunk.project_id = metadata.project_id
            chunk.access_scope = metadata.access_scope

        jobs[ingestion_id]["status"] = DocumentStatus.INDEXING
        client = KnowledgeEngineClient()
        indexed = 0
        for chunk in chunks:
            await client.ingest(chunk)
            indexed += 1

        superseded_version = None
        if metadata.supersedes and ":v" in metadata.supersedes:
            try:
                superseded_version = int(metadata.supersedes.rsplit(":v", 1)[1])
            except ValueError:
                superseded_version = None

        finalized = await repository.finalize_version(document_id, metadata.version)

        await client.set_lifecycle_status(
            document_id=document_id,
            version=metadata.version,
            lifecycle_status=finalized.lifecycle_status.value,
        )

        if superseded_version is not None and superseded_version != metadata.version:
            await client.set_lifecycle_status(
                document_id=document_id,
                version=superseded_version,
                lifecycle_status=LifecycleStatus.SUPERSEDED.value,
            )
        jobs[ingestion_id]["status"] = DocumentStatus.READY
        jobs[ingestion_id]["lifecycle_status"] = finalized.lifecycle_status

        return IngestResponse(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=metadata.version,
            lifecycle_status=finalized.lifecycle_status,
            status=DocumentStatus.READY,
            content_hash=content_hash,
            chunk_count=len(chunks),
            indexed_count=indexed,
            warnings=warnings,
        )

    except DuplicateDocumentError as e:
        jobs[ingestion_id]["status"] = DocumentStatus.FAILED_PARSING
        return IngestResponse(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=requested_version,
            lifecycle_status=LifecycleStatus.ARCHIVED,
            status=DocumentStatus.FAILED_PARSING,
            content_hash=content_hash,
            chunk_count=0,
            indexed_count=0,
            error_code="DOCUMENT_ALREADY_INGESTED",
            error=str(e),
        )
    except VersionConflictError as e:
        jobs[ingestion_id]["status"] = DocumentStatus.FAILED_PARSING
        return IngestResponse(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=requested_version,
            lifecycle_status=LifecycleStatus.ARCHIVED,
            status=DocumentStatus.FAILED_PARSING,
            content_hash=content_hash,
            chunk_count=0,
            indexed_count=0,
            error_code="VERSION_ALREADY_EXISTS",
            error=str(e),
        )
    except ValueError as e:
        code = str(e)
        status = (
            DocumentStatus.FAILED_SECURITY
            if code in {"INVALID_FILENAME", "FILE_TOO_LARGE", "UNSUPPORTED_FILE_TYPE"}
            else DocumentStatus.FAILED_PARSING
        )
        if registered_version is not None:
            await repository.fail_version(document_id, registered_version)
        jobs[ingestion_id] = {
            "document_id": document_id,
            "version": registered_version or requested_version,
            "status": status,
            "error_code": code,
            "error": code,
        }
        return IngestResponse(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=registered_version or requested_version,
            lifecycle_status=LifecycleStatus.ARCHIVED,
            status=status,
            content_hash=content_hash,
            chunk_count=0,
            indexed_count=0,
            error_code=code,
            error=code,
        )
    except Exception as e:
        if registered_version is not None:
            await repository.fail_version(document_id, registered_version)
        jobs[ingestion_id] = {
            "document_id": document_id,
            "version": registered_version or requested_version,
            "status": DocumentStatus.FAILED_INDEXING,
            "error_code": "INGESTION_ERROR",
            "error": str(e),
        }
        return IngestResponse(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=registered_version or requested_version,
            lifecycle_status=LifecycleStatus.ARCHIVED,
            status=DocumentStatus.FAILED_INDEXING,
            content_hash=content_hash,
            chunk_count=0,
            indexed_count=0,
            error_code="INGESTION_ERROR",
            error=str(e),
        )


def get_job(ingestion_id: str):
    return jobs.get(ingestion_id)
