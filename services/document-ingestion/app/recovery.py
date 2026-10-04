"""Explicit, idempotent recovery for interrupted document indexing.

This module intentionally exposes a callable recovery operation instead of
running it during service startup. Operators can first inspect the durable
job/version and choose exactly which INGESTING version to replay.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from mimetypes import guess_type

from .chunker import chunk_document
from .extractors import extract_document_from_path
from .knowledge_client import KnowledgeEngineClient
from .metadata import update_ingestion_jobs_for_version
from .models import (
    DocumentMetadata,
    DocumentStatus,
    LifecycleStatus,
    NormalizedDocument,
)
from .repository import RepositoryError, repository
from .vision import analyze_sparse_pdf_pages


async def recover_ingesting_version(document_id: str, version: int) -> dict:
    """Replay canonical bytes into the index using stable chunk identifiers.

    The source is verified against its stored SHA-256 before extraction. Qdrant
    upserts are deterministic, so rerunning after a partial failure replaces
    the same point IDs instead of duplicating points. No canonical data is
    deleted on either successful or failed replay.
    """
    version_metadata = await repository.get_version(document_id, version)
    if version_metadata is None:
        raise RepositoryError("DOCUMENT_VERSION_NOT_FOUND")
    if version_metadata.lifecycle_status not in {
        LifecycleStatus.INGESTING,
        LifecycleStatus.CURRENT,
    }:
        raise RepositoryError("VERSION_NOT_RECOVERABLE")
    if Path(version_metadata.source_file).name != version_metadata.source_file:
        raise RepositoryError("INVALID_CANONICAL_FILENAME")

    await update_ingestion_jobs_for_version(
        document_id,
        version,
        status=DocumentStatus.RECOVERING.value,
        lifecycle_status=version_metadata.lifecycle_status.value,
        error_code=None,
        error=None,
    )

    with TemporaryDirectory(prefix="corporate-ai-recovery-") as temp_dir:
        source_path = Path(temp_dir) / Path(version_metadata.source_file).name
        metadata = await repository.copy_validated_canonical_source(
            document_id,
            version,
            str(source_path),
        )

        document_metadata = DocumentMetadata(
            document_id=metadata.document_id,
            source_system=metadata.source_system,
            source_reference=metadata.source_reference,
            title=metadata.title,
            author=metadata.author,
            classification=metadata.classification,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
            language=metadata.language,
            version=metadata.version,
            document_date=metadata.document_date,
            effective_from=metadata.effective_from,
            effective_to=metadata.effective_to,
            lifecycle_status=metadata.lifecycle_status,
            parent_document_id=metadata.parent_document_id,
            supersedes=metadata.supersedes,
            superseded_by=metadata.superseded_by,
            project_id=metadata.project_id,
            access_scope=metadata.access_scope,
            canonical_storage_key=metadata.canonical_storage_key,
        )
        blocks = extract_document_from_path(metadata.source_file, source_path)
        if source_path.suffix.lower() == ".pdf":
            from .pipeline import _vision_result_to_blocks

            vision_results = await analyze_sparse_pdf_pages(source_path, blocks)
            for result in vision_results:
                blocks.extend(_vision_result_to_blocks(result, metadata.source_file))

    if not blocks:
        raise RepositoryError("RECOVERY_EMPTY_DOCUMENT")

    document = NormalizedDocument(
        document_id=metadata.document_id,
        source_file=metadata.source_file,
        media_type=guess_type(metadata.source_file)[0] or "application/octet-stream",
        content_hash=metadata.content_hash,
        metadata=document_metadata,
        blocks=blocks,
    )
    chunks = chunk_document(document)
    if not chunks:
        raise RepositoryError("RECOVERY_EMPTY_INDEXABLE_CONTENT")
    client = KnowledgeEngineClient()
    for chunk in chunks:
        chunk.lifecycle_status = LifecycleStatus.INGESTING
        chunk.version = metadata.version
        chunk.document_date = metadata.document_date
        chunk.effective_from = metadata.effective_from
        chunk.effective_to = metadata.effective_to
        chunk.project_id = metadata.project_id
        chunk.classification = metadata.classification or "INTERNAL"
        chunk.canonical_source_verified = True
        chunk.canonical_storage_key = metadata.canonical_storage_key
        chunk.access_scope = metadata.access_scope
        await client.ingest(chunk)

    # Invalidate the predecessor before making this version current in either
    # store. A failure after this point can temporarily yield no current result,
    # but cannot leave stale predecessor vectors retrievable as current truth.
    if metadata.supersedes and ":v" in metadata.supersedes:
        try:
            previous_version = int(metadata.supersedes.rsplit(":v", 1)[1])
        except ValueError:
            previous_version = None
        if previous_version is not None and previous_version != version:
            await client.set_lifecycle_status(
                document_id=document_id,
                version=previous_version,
                lifecycle_status=LifecycleStatus.SUPERSEDED.value,
            )

    if metadata.lifecycle_status == LifecycleStatus.INGESTING:
        finalized = await repository.finalize_version(document_id, version)
    else:
        finalized = document_metadata

    await client.set_lifecycle_status(
        document_id=document_id,
        version=version,
        lifecycle_status=finalized.lifecycle_status.value,
    )

    await update_ingestion_jobs_for_version(
        document_id,
        version,
        status=DocumentStatus.READY.value,
        lifecycle_status=finalized.lifecycle_status.value,
        error_code=None,
        error=None,
    )
    return {
        "status": DocumentStatus.READY.value,
        "document_id": document_id,
        "version": version,
        "chunk_count": len(chunks),
        "lifecycle_status": finalized.lifecycle_status.value,
    }
