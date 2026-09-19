from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

class AnswerStatus(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NO_ANSWER = "NO_ANSWER"

class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.45, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    score: float
    document_id: str | None = None
    source_file: str | None = None
    page: int | None = None
    page_type: str | None = None
    chunk_type: str | None = None
    section: str | None = None
    confidence: float | None = None
    chunk_id: str | None = None
    content: str

class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]

class IngestRequest(BaseModel):
    document_id: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    content: str = Field(min_length=1)
    page: int | None = None
    page_type: str = "TEXT"
    chunk_type: str = "text"
    section: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class IngestResponse(BaseModel):
    status: str
    point_id: str
    vector_dimensions: int

class RAGQuery(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.45, ge=0.0, le=1.0)

class Source(BaseModel):
    document_id: str | None = None
    source_file: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    score: float
    content: str

class ClaimEvidence(BaseModel):
    source_id: int
    document_id: str | None = None
    source_file: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    score: float | None = None
    content: str

class Claim(BaseModel):
    text: str
    supported: bool
    source_ids: list[int] = Field(default_factory=list)
    evidence: list[ClaimEvidence] = Field(default_factory=list)
    reason: str = ""

class RAGResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    answer_status: AnswerStatus
    evidence_status: EvidenceStatus
    evidence_claims: list[dict[str, Any]] = Field(default_factory=list)
    evidence_reason: str
    claims: list[Claim] = Field(default_factory=list)
    sources: list[Source]

class HealthResponse(BaseModel):
    status: str
    qdrant: bool
    embedding: bool
    llm: bool
    collection: str
    embedding_model: str
    llm_model: str
    version: str
