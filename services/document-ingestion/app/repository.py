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
)
from .models import DocumentMetadata, DocumentVersionResponse


class RepositoryError(MetadataError):
    """Base error exposed by the Repository boundary."""


class Repository(Protocol):
    """Canonical document repository contract used by ingestion.

    The initial adapter deliberately delegates version/lifecycle persistence
    to the existing metadata implementation. Canonical source storage,
    ACLs, scopes, audit and object-storage adapters are added behind this
    boundary in later phases.
    """

    async def register_version(
        self,
        metadata: DocumentMetadata,
        source_file: str,
        content_hash: str,
    ) -> DocumentMetadata: ...

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
    """Repository adapter backed by the existing PostgreSQL metadata store."""

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
