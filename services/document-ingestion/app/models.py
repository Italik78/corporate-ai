from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    RECEIVED = "RECEIVED"
    SECURITY_CHECK = "SECURITY_CHECK"
    ROUTING = "ROUTING"
    EXTRACTING = "EXTRACTING"
    NORMALIZING = "NORMALIZING"
    METADATA = "METADATA"
    DEDUPLICATING = "DEDUPLICATING"
    CHUNKING = "CHUNKING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED_SECURITY = "FAILED_SECURITY"
    FAILED_PARSING = "FAILED_PARSING"
    FAILED_NORMALIZATION = "FAILED_NORMALIZATION"
    FAILED_INDEXING = "FAILED_INDEXING"


class LifecycleStatus(str, Enum):
    INGESTING = "INGESTING"
    CURRENT = "CURRENT"
    SUPERSEDED = "SUPERSEDED"
    ARCHIVED = "ARCHIVED"


class DocumentMetadata(BaseModel):
    document_id: str
    source_system: str = "upload"
    title: str
    author: str | None = None
    classification: str = "INTERNAL"
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
    language: str = "bg"
    version: int = 1
    document_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    lifecycle_status: LifecycleStatus = LifecycleStatus.INGESTING
    parent_document_id: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    project_id: str | None = None
    access_scope: str = "INTERNAL"


class NormalizedBlock(BaseModel):
    block_id: str
    block_type: str = "text"
    content: str
    page: int | None = None
    section: str | None = None
    confidence: float = 1.0
    provenance: dict[str, Any] = Field(default_factory=dict)


class NormalizedDocument(BaseModel):
    document_id: str
    source_file: str
    media_type: str
    content_hash: str
    metadata: DocumentMetadata
    blocks: list[NormalizedBlock]


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    source_file: str
    version: int = 1
    lifecycle_status: LifecycleStatus = LifecycleStatus.INGESTING
    document_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    project_id: str | None = None
    access_scope: str = "INTERNAL"
    page: int | None = None
    page_type: str = "TEXT"
    chunk_type: str = "text"
    section: str | None = None
    confidence: float = 1.0
    content: str
    provenance: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    ingestion_id: str
    document_id: str
    version: int
    lifecycle_status: LifecycleStatus
    status: DocumentStatus
    content_hash: str
    chunk_count: int
    indexed_count: int
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error: str | None = None


class StatusResponse(BaseModel):
    ingestion_id: str
    document_id: str
    status: DocumentStatus
    error_code: str | None = None
    error: str | None = None


class DocumentVersionResponse(BaseModel):
    document_id: str
    version: int
    source_file: str
    content_hash: str
    source_system: str
    title: str
    author: str | None = None
    classification: str
    language: str
    document_date: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    lifecycle_status: LifecycleStatus
    parent_document_id: str | None = None
    supersedes: str | None = None
    superseded_by: str | None = None
    project_id: str | None = None
    access_scope: str
    created_at: str
    updated_at: str
