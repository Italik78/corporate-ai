from datetime import datetime, timezone
import hashlib
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import fitz

from .chunker import chunk_document
from .config import settings
from .extractors import extract_document, extract_document_from_path
from .knowledge_client import KnowledgeEngineClient
from .vision import VisionError, analyze_sparse_pdf_pages
from .metadata import (
    create_ingestion_job,
    find_document_by_source_reference,
    find_duplicate_version,
    get_ingestion_job,
    update_ingestion_job,
)
from .repository import (
    DuplicateDocumentError,
    VersionConflictError,
    repository,
)
from .models import (
    DocumentMetadata,
    DocumentProcessResponse,
    DocumentStatus,
    IngestResponse,
    LifecycleStatus,
    NormalizedBlock,
    NormalizedDocument,
)
from .security import (
    security_scan,
    security_scan_file,
    sha256_bytes,
    validate_extension,
    validate_file_size,
    validate_filename,
    validate_size,
)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vision_result_to_blocks(
    result: dict,
    filename: str,
) -> list[NormalizedBlock]:
    page = int(result["_page"])
    confidence = float(result.get("confidence", 0.0))
    blocks: list[NormalizedBlock] = []

    text = str(result.get("text") or "").strip()
    title = str(result.get("title") or "").strip()

    if title:
        text = f"{title}\n{text}".strip()

    tables = result.get("tables") or []
    for table_index, table in enumerate(tables, start=1):
        headers = table.get("headers") or []
        rows = table.get("rows") or []
        lines: list[str] = []
        if headers:
            lines.append(" | ".join(str(value) if value is not None else "" for value in headers))
        for row in rows:
            lines.append(" | ".join(str(value) if value is not None else "" for value in row))
        table_text = "\n".join(lines).strip()
        if table_text:
            blocks.append(
                NormalizedBlock(
                    block_id=f"pdf-p{page:04d}-vision-table{table_index:04d}",
                    block_type="table",
                    content=table_text,
                    page=page,
                    confidence=confidence,
                    provenance={
                        "source_format": "pdf",
                        "page": page,
                        "extraction": "qwen3_6_vision",
                        "page_type": result.get("page_type"),
                        "uncertain_items": result.get("uncertain_items", []),
                    },
                )
            )

    if text:
        blocks.append(
            NormalizedBlock(
                block_id=f"pdf-p{page:04d}-vision-text",
                block_type="text",
                content=text,
                page=page,
                confidence=confidence,
                provenance={
                    "source_format": "pdf",
                    "page": page,
                    "extraction": "qwen3_6_vision",
                    "page_type": result.get("page_type"),
                    "uncertain_items": result.get("uncertain_items", []),
                },
            )
        )

    return blocks


async def _update_job(
    ingestion_id: str,
    *,
    document_id: str | None = None,
    version: int | None = None,
    status: DocumentStatus | None = None,
    lifecycle_status: LifecycleStatus | None = None,
    error_code: str | None = None,
    error: str | None = None,
) -> None:
    await update_ingestion_job(
        ingestion_id,
        document_id=document_id,
        version=version,
        status=status.value if status is not None else None,
        lifecycle_status=(
            lifecycle_status.value if lifecycle_status is not None else None
        ),
        error_code=error_code,
        error=error,
    )


def _pdf_page_count(path: str | Path | None = None, data: bytes | None = None) -> int:
    if path is not None:
        document = fitz.open(str(path))
    elif data is not None:
        document = fitz.open(stream=data, filetype="pdf")
    else:
        raise ValueError("PDF_PAGE_COUNT_INPUT_MISSING")

    try:
        return document.page_count
    finally:
        document.close()


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


async def _stage_upload(upload) -> tuple[Path, str, int]:
    staging_dir = Path(settings.staging_storage_path)
    staging_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = settings.max_file_size_mb * 1024 * 1024
    chunk_size = settings.upload_chunk_size_bytes
    digest = hashlib.sha256()
    total = 0

    temporary = NamedTemporaryFile(
        mode="wb",
        dir=staging_dir,
        prefix=".ingest-",
        suffix=Path(upload.filename or "").suffix.lower() or ".upload",
        delete=False,
    )
    staged_path = Path(temporary.name)

    try:
        with temporary:
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("FILE_TOO_LARGE")
                digest.update(chunk)
                temporary.write(chunk)
            temporary.flush()
        return staged_path, digest.hexdigest(), total
    except Exception:
        staged_path.unlink(missing_ok=True)
        raise


def _normalized_document_from_chunks(
    duplicate,
    chunks: list[dict],
    ingestion_id: str,
) -> DocumentProcessResponse:
    if not chunks:
        raise ValueError("DUPLICATE_CONTENT_NOT_INDEXED")

    ordered_chunks = sorted(
        chunks,
        key=lambda chunk: (
            chunk.get("page") is None,
            chunk.get("page") if chunk.get("page") is not None else 0,
            str(chunk.get("chunk_id") or ""),
        ),
    )

    blocks = [
        NormalizedBlock(
            block_id=str(chunk.get("chunk_id") or ""),
            block_type=str(chunk.get("chunk_type") or "text"),
            content=str(chunk.get("content") or ""),
            page=chunk.get("page"),
            section=chunk.get("section"),
            confidence=float(chunk.get("confidence", 1.0)),
            provenance=chunk.get("provenance") or {},
        )
        for chunk in ordered_chunks
        if str(chunk.get("content") or "").strip()
    ]

    if not blocks:
        raise ValueError("DUPLICATE_CONTENT_EMPTY_INDEX")

    metadata = DocumentMetadata(
        document_id=duplicate.document_id,
        source_system=duplicate.source_system,
        source_reference=duplicate.source_reference,
        title=duplicate.title,
        author=duplicate.author,
        classification=duplicate.classification,
        created_at=duplicate.created_at,
        updated_at=duplicate.updated_at,
        tags=[],
        language=duplicate.language,
        version=duplicate.version,
        document_date=duplicate.document_date,
        effective_from=duplicate.effective_from,
        effective_to=duplicate.effective_to,
        lifecycle_status=(
            LifecycleStatus(duplicate.lifecycle_status)
            if not isinstance(duplicate.lifecycle_status, LifecycleStatus)
            else duplicate.lifecycle_status
        ),
        parent_document_id=duplicate.parent_document_id,
        supersedes=duplicate.supersedes,
        superseded_by=duplicate.superseded_by,
        project_id=duplicate.project_id,
        access_scope=duplicate.access_scope,
        canonical_storage_key=duplicate.canonical_storage_key,
    )

    return DocumentProcessResponse(
        ingestion_id=ingestion_id,
        document=NormalizedDocument(
            document_id=duplicate.document_id,
            source_file=duplicate.source_file,
            media_type=_media_type(duplicate.source_file),
            content_hash=duplicate.content_hash,
            metadata=metadata,
            blocks=blocks,
        ),
    )


async def ingest_document(
    filename: str,
    data: bytes | None = None,
    document_id: str | None = None,
    source_system: str = "upload",
    source_reference: str | None = None,
    version: int | None = None,
    document_date: str | None = None,
    effective_from: str | None = None,
    effective_to: str | None = None,
    project_id: str | None = None,
    access_scope: str = "INTERNAL",
    author: str | None = None,
    classification: str = "INTERNAL",
    tags: list[str] | None = None,
    upload=None,
    return_document: bool = False,
) -> IngestResponse | DocumentProcessResponse:
    ingestion_id = str(uuid4())

    if document_id is None and source_reference:
        document_id = await find_document_by_source_reference(
            source_system=source_system,
            source_reference=source_reference,
        )

    document_id = document_id or str(uuid4())
    requested_version = version or 1

    await create_ingestion_job(
        ingestion_id=ingestion_id,
        document_id=document_id,
        version=requested_version,
        status=DocumentStatus.RECEIVED.value,
    )

    staged_path: Path | None = None
    page_count: int | None = None
    content_hash = sha256_bytes(data) if data is not None else ""
    registered_version: int | None = None
    canonical_storage_key: str | None = None

    try:
        if data is not None and upload is not None:
            raise ValueError("MULTIPLE_INPUTS")
        if data is None and upload is None:
            raise ValueError("EMPTY_INPUT")

        filename = validate_filename(filename)
        validate_extension(filename, settings.allowed_suffixes)

        if upload is not None:
            staged_path, content_hash, _ = await _stage_upload(upload)
            validate_file_size(
                staged_path,
                settings.max_file_size_mb * 1024 * 1024,
            )
            await _update_job(ingestion_id, status=DocumentStatus.SECURITY_CHECK)
            warnings = security_scan_file(
                staged_path,
                Path(filename).suffix.lower(),
                settings.upload_chunk_size_bytes,
            )
        else:
            validate_size(data, settings.max_file_size_mb * 1024 * 1024)
            await _update_job(ingestion_id, status=DocumentStatus.SECURITY_CHECK)
            warnings = security_scan(data, Path(filename).suffix.lower())

        if Path(filename).suffix.lower() == ".pdf":
            page_count = _pdf_page_count(
                path=staged_path,
                data=data if staged_path is None else None,
            )

        await _update_job(ingestion_id, status=DocumentStatus.DEDUPLICATING)
        duplicate = await find_duplicate_version(
            content_hash=content_hash,
            project_id=project_id,
            access_scope=access_scope,
        )
        if duplicate is not None:
            duplicate_lifecycle_status = (
                LifecycleStatus(duplicate.lifecycle_status)
                if not isinstance(duplicate.lifecycle_status, LifecycleStatus)
                else duplicate.lifecycle_status
            )

            await _update_job(
                ingestion_id,
                document_id=duplicate.document_id,
                version=duplicate.version,
                status=DocumentStatus.READY,
                lifecycle_status=duplicate_lifecycle_status,
            )

            if return_document:
                client = KnowledgeEngineClient()
                chunks = await client.get_document_chunks(
                    document_id=duplicate.document_id,
                    version=duplicate.version,
                )
                return _normalized_document_from_chunks(
                    duplicate=duplicate,
                    chunks=chunks,
                    ingestion_id=ingestion_id,
                )

            client = KnowledgeEngineClient()
            chunks = await client.get_document_chunks(
                document_id=duplicate.document_id,
                version=duplicate.version,
            )

            return IngestResponse(
                ingestion_id=ingestion_id,
                document_id=duplicate.document_id,
                version=duplicate.version,
                lifecycle_status=duplicate_lifecycle_status,
                status=DocumentStatus.READY,
                content_hash=duplicate.content_hash,
                chunk_count=len(chunks),
                indexed_count=len(chunks),
                page_count=page_count,
                warnings=warnings + ["DUPLICATE_CONTENT_REUSED"],
            )

        await _update_job(ingestion_id, status=DocumentStatus.ROUTING)
        await _update_job(ingestion_id, status=DocumentStatus.EXTRACTING)
        blocks = (
            extract_document_from_path(filename, staged_path)
            if staged_path is not None
            else extract_document(filename, data)
        )

        if (
            staged_path is not None
            and Path(filename).suffix.lower() == ".pdf"
        ):
            vision_results = await analyze_sparse_pdf_pages(
                staged_path,
                blocks,
            )
            for vision_result in vision_results:
                blocks.extend(
                    _vision_result_to_blocks(
                        vision_result,
                        filename,
                    )
                )

        if not blocks:
            raise ValueError("EMPTY_DOCUMENT")

        await _update_job(ingestion_id, status=DocumentStatus.NORMALIZING)
        metadata = DocumentMetadata(
            document_id=document_id,
            source_system=source_system,
            source_reference=source_reference,
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

        await _update_job(ingestion_id, status=DocumentStatus.METADATA)
        metadata = await repository.register_version(
            metadata=metadata,
            source_file=filename,
            content_hash=content_hash,
        )
        registered_version = metadata.version
        await _update_job(ingestion_id, version=registered_version)

        if staged_path is not None:
            canonical_storage_key = await repository.store_canonical_source_file(
                document_id=document_id,
                version=registered_version,
                filename=filename,
                source_path=str(staged_path),
                content_hash=content_hash,
            )
        else:
            canonical_storage_key = await repository.store_canonical_source(
                document_id=document_id,
                version=registered_version,
                filename=filename,
                data=data,
                content_hash=content_hash,
            )
        await repository.set_canonical_storage_key(
            document_id=document_id,
            version=registered_version,
            canonical_storage_key=canonical_storage_key,
        )

        # register_version() may resolve an automatically assigned version and
        # populate supersedes metadata. Chunk IDs must use the resolved version,
        # not the initially requested version captured in the original document.
        doc.metadata = metadata

        await _update_job(ingestion_id, status=DocumentStatus.DEDUPLICATING)
        await _update_job(ingestion_id, status=DocumentStatus.CHUNKING)
        chunks = chunk_document(doc)

        for chunk in chunks:
            chunk.version = metadata.version
            chunk.lifecycle_status = LifecycleStatus.INGESTING
            chunk.document_date = metadata.document_date
            chunk.effective_from = metadata.effective_from
            chunk.effective_to = metadata.effective_to
            chunk.project_id = metadata.project_id
            chunk.access_scope = metadata.access_scope

        await _update_job(ingestion_id, status=DocumentStatus.INDEXING)
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
        await _update_job(
            ingestion_id,
            status=DocumentStatus.READY,
            lifecycle_status=finalized.lifecycle_status,
        )

        if return_document:
            return DocumentProcessResponse(
                ingestion_id=ingestion_id,
                document=doc,
            )

        return IngestResponse(
            ingestion_id=ingestion_id,
            document_id=document_id,
            version=metadata.version,
            lifecycle_status=finalized.lifecycle_status,
            status=DocumentStatus.READY,
            content_hash=content_hash,
            chunk_count=len(chunks),
            indexed_count=indexed,
            page_count=page_count,
            warnings=warnings,
        )

    except DuplicateDocumentError as e:
        await _update_job(
            ingestion_id,
            status=DocumentStatus.FAILED_PARSING,
            error_code="DOCUMENT_ALREADY_INGESTED",
            error=str(e),
        )
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
        await _update_job(
            ingestion_id,
            status=DocumentStatus.FAILED_PARSING,
            error_code="VERSION_ALREADY_EXISTS",
            error=str(e),
        )
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
        if canonical_storage_key is not None:
            await repository.delete_canonical_source(
                document_id, registered_version, filename
            )
        await _update_job(
            ingestion_id,
            document_id=document_id,
            version=registered_version or requested_version,
            status=status,
            error_code=code,
            error=code,
        )
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
        if canonical_storage_key is not None:
            try:
                await repository.delete_canonical_source(
                    document_id, registered_version, filename
                )
            except Exception:
                pass
        await _update_job(
            ingestion_id,
            document_id=document_id,
            version=registered_version or requested_version,
            status=DocumentStatus.FAILED_INDEXING,
            error_code="INGESTION_ERROR",
            error=str(e),
        )
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
    finally:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)


async def get_job(ingestion_id: str):
    return await get_ingestion_job(ingestion_id)
