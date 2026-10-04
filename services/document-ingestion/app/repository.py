from __future__ import annotations

from typing import Protocol

from .metadata import (
    DuplicateDocumentError,
    MetadataError,
    VersionConflictError,
    fail_version,
    finalize_version,
    get_version,
    list_versions,
    register_version,
    set_canonical_storage_key,
)
from .models import DocumentMetadata, DocumentVersionResponse
from .reconciliation import (
    ReconciliationState,
    VersionIntegrity,
    inspect_canonical_source,
)
from .storage import CanonicalStorageError, FilesystemCanonicalStorage


class RepositoryError(MetadataError):
    """Base error exposed by the Repository boundary."""


class Repository(Protocol):
    """Canonical document repository contract used by ingestion.

    Version/lifecycle metadata remains backed by PostgreSQL while canonical
    source bytes are stored through the repository's storage adapter.
    ACLs, scopes, audit and external repository adapters remain future phases.
    """

    async def register_version(
        self,
        metadata: DocumentMetadata,
        source_file: str,
        content_hash: str,
    ) -> DocumentMetadata: ...

    async def store_canonical_source(
        self,
        document_id: str,
        version: int,
        filename: str,
        data: bytes,
        content_hash: str,
    ) -> str: ...

    async def store_canonical_source_file(
        self,
        document_id: str,
        version: int,
        filename: str,
        source_path: str,
        content_hash: str,
    ) -> str: ...

    async def set_canonical_storage_key(
        self, document_id: str, version: int, canonical_storage_key: str
    ) -> None: ...

    async def read_canonical_source(
        self,
        document_id: str,
        version: int,
        filename: str,
    ) -> bytes: ...

    async def delete_canonical_source(
        self,
        document_id: str,
        version: int,
        filename: str,
    ) -> None: ...

    async def finalize_version(
        self,
        document_id: str,
        version: int,
    ) -> DocumentMetadata: ...

    async def inspect_version_integrity(
        self, document_id: str, version: int
    ) -> VersionIntegrity: ...

    async def read_validated_canonical_source(
        self, document_id: str, version: int
    ) -> tuple[DocumentVersionResponse, bytes]: ...

    async def repair_missing_canonical_key(
        self, document_id: str, version: int
    ) -> VersionIntegrity: ...

    async def copy_validated_canonical_source(
        self, document_id: str, version: int, destination: str
    ) -> DocumentVersionResponse: ...

    async def fail_version(self, document_id: str, version: int) -> None: ...

    async def list_versions(
        self, document_id: str
    ) -> list[DocumentVersionResponse]: ...

    async def get_version(
        self, document_id: str, version: int
    ) -> DocumentVersionResponse | None: ...


class PostgresRepository:
    """Repository adapter backed by PostgreSQL metadata and canonical storage."""

    def __init__(self, storage: FilesystemCanonicalStorage | None = None):
        self.storage = storage or FilesystemCanonicalStorage()

    async def register_version(
        self,
        metadata: DocumentMetadata,
        source_file: str,
        content_hash: str,
    ) -> DocumentMetadata:
        try:
            return await register_version(metadata, source_file, content_hash)
        except (DuplicateDocumentError, VersionConflictError):
            raise
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc

    async def store_canonical_source(
        self,
        document_id: str,
        version: int,
        filename: str,
        data: bytes,
        content_hash: str,
    ) -> str:
        try:
            return self.storage.store(
                document_id=document_id,
                version=version,
                filename=filename,
                data=data,
                content_hash=content_hash,
            )
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc

    async def store_canonical_source_file(
        self,
        document_id: str,
        version: int,
        filename: str,
        source_path: str,
        content_hash: str,
    ) -> str:
        try:
            return self.storage.store_file(
                document_id=document_id,
                version=version,
                filename=filename,
                source_path=source_path,
                content_hash=content_hash,
            )
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc

    async def set_canonical_storage_key(
        self, document_id: str, version: int, canonical_storage_key: str
    ) -> None:
        try:
            await set_canonical_storage_key(document_id, version, canonical_storage_key)
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc

    async def read_canonical_source(
        self,
        document_id: str,
        version: int,
        filename: str,
    ) -> bytes:
        try:
            return self.storage.read(document_id, version, filename)
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc

    async def delete_canonical_source(
        self,
        document_id: str,
        version: int,
        filename: str,
    ) -> None:
        try:
            self.storage.delete(document_id, version, filename)
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc

    async def finalize_version(
        self,
        document_id: str,
        version: int,
    ) -> DocumentMetadata:
        integrity = await self.inspect_version_integrity(document_id, version)
        if integrity.state.value != "REPAIRABLE":
            raise RepositoryError(
                f"CANONICAL_SOURCE_NOT_FINALIZABLE:{integrity.state.value}:{integrity.reason}"
            )
        try:
            return await finalize_version(document_id, version)
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc

    async def inspect_version_integrity(
        self, document_id: str, version: int
    ) -> VersionIntegrity:
        metadata = await get_version(document_id, version)
        if metadata is None:
            raise RepositoryError("DOCUMENT_VERSION_NOT_FOUND")
        return inspect_canonical_source(metadata, self.storage)

    async def read_validated_canonical_source(
        self, document_id: str, version: int
    ) -> tuple[DocumentVersionResponse, bytes]:
        metadata = await get_version(document_id, version)
        if metadata is None:
            raise RepositoryError("DOCUMENT_VERSION_NOT_FOUND")
        integrity = inspect_canonical_source(metadata, self.storage)
        if integrity.state not in {
            ReconciliationState.VALID,
            ReconciliationState.REPAIRABLE,
        }:
            raise RepositoryError(
                f"CANONICAL_SOURCE_UNAVAILABLE:{integrity.state.value}:{integrity.reason}"
            )
        if metadata.canonical_storage_key is None:
            raise RepositoryError("CANONICAL_KEY_REPAIR_REQUIRES_EXPLICIT_ACTION")
        try:
            data = self.storage.verify_key(
                metadata.canonical_storage_key,
                metadata.content_hash,
            )
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc
        return metadata, data

    async def copy_validated_canonical_source(
        self,
        document_id: str,
        version: int,
        destination: str,
    ) -> DocumentVersionResponse:
        metadata = await get_version(document_id, version)
        if metadata is None:
            raise RepositoryError("DOCUMENT_VERSION_NOT_FOUND")
        integrity = inspect_canonical_source(metadata, self.storage)
        if integrity.state not in {
            ReconciliationState.VALID,
            ReconciliationState.REPAIRABLE,
        }:
            raise RepositoryError(
                f"CANONICAL_SOURCE_UNAVAILABLE:{integrity.state.value}:{integrity.reason}"
            )
        if metadata.canonical_storage_key is None:
            raise RepositoryError("CANONICAL_KEY_REPAIR_REQUIRES_EXPLICIT_ACTION")
        try:
            self.storage.copy_verified_key(
                metadata.canonical_storage_key,
                metadata.content_hash,
                destination,
            )
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc
        return metadata

    async def repair_missing_canonical_key(
        self, document_id: str, version: int
    ) -> VersionIntegrity:
        """Persist a missing key only after verifying the predicted bytes/hash.

        This is deliberately an explicit repository operation. It is not run
        during startup or normal ingestion and never changes lifecycle state.
        """
        metadata = await get_version(document_id, version)
        if metadata is None:
            raise RepositoryError("DOCUMENT_VERSION_NOT_FOUND")
        integrity = inspect_canonical_source(metadata, self.storage)
        if (
            integrity.state != ReconciliationState.REPAIRABLE
            or not integrity.candidate_storage_key
            or metadata.canonical_storage_key is not None
        ):
            raise RepositoryError(
                f"CANONICAL_KEY_NOT_REPAIRABLE:{integrity.state.value}:{integrity.reason}"
            )
        try:
            self.storage.verify_key_hash(
                integrity.candidate_storage_key,
                metadata.content_hash,
            )
            await set_canonical_storage_key(
                document_id,
                version,
                integrity.candidate_storage_key,
            )
        except CanonicalStorageError as exc:
            raise RepositoryError(str(exc)) from exc
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc
        updated = await get_version(document_id, version)
        if updated is None:
            raise RepositoryError("DOCUMENT_VERSION_NOT_FOUND")
        return inspect_canonical_source(updated, self.storage)

    async def fail_version(self, document_id: str, version: int) -> None:
        try:
            await fail_version(document_id, version)
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc

    async def list_versions(
        self, document_id: str
    ) -> list[DocumentVersionResponse]:
        try:
            return await list_versions(document_id)
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc

    async def get_version(
        self, document_id: str, version: int
    ) -> DocumentVersionResponse | None:
        try:
            return await get_version(document_id, version)
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc


repository = PostgresRepository()
