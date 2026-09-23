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

    async def set_canonical_storage_key(
        self, document_id: str, version: int, canonical_storage_key: str
    ) -> None: ...

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
        try:
            return await finalize_version(document_id, version)
        except MetadataError as exc:
            raise RepositoryError(str(exc)) from exc

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
