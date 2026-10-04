from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    REQUESTED = "REQUESTED"
    UNDERSTANDING = "UNDERSTANDING"
    CONTEXT_CHECK = "CONTEXT_CHECK"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    CLASSIFIED = "CLASSIFIED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    EVIDENCE_EVALUATION = "EVIDENCE_EVALUATION"
    MORE_EVIDENCE_REQUIRED = "MORE_EVIDENCE_REQUIRED"
    CONFLICT_ANALYSIS = "CONFLICT_ANALYSIS"
    APPLICABILITY_CHECK = "APPLICABILITY_CHECK"
    VERIFICATION = "VERIFICATION"
    ANSWER = "ANSWER"
    CONDITIONAL_ANSWER = "CONDITIONAL_ANSWER"
    NO_ANSWER = "NO_ANSWER"
    TRACE_COMPLETE = "TRACE_COMPLETE"


class TaskType(str, Enum):
    GENERAL = "GENERAL"
    CORPORATE_KNOWLEDGE = "CORPORATE_KNOWLEDGE"
    WEB_RESEARCH = "WEB_RESEARCH"
    CORPORATE_AND_WEB = "CORPORATE_AND_WEB"
    CLARIFICATION = "CLARIFICATION"
    UNKNOWN = "UNKNOWN"


class SourceClass(str, Enum):
    CORPORATE = "CORPORATE"
    WEB = "WEB"
    SYSTEM = "SYSTEM"


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONFLICT = "CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_REQUIRED = "NOT_REQUIRED"


class AnswerStatus(str, Enum):
    GROUNDED = "GROUNDED"
    CONDITIONAL = "CONDITIONAL"
    GENERAL = "GENERAL"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    NO_ANSWER = "NO_ANSWER"


class QuestionResolution(str, Enum):
    ANSWERABLE = "ANSWERABLE"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTED = "CONFLICTED"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class CapabilityType(str, Enum):
    CORPORATE_RETRIEVAL = "CORPORATE_RETRIEVAL"
    WEB_SEARCH = "WEB_SEARCH"
    WEB_FETCH = "WEB_FETCH"
    LLM_REASONING = "LLM_REASONING"
    VERIFICATION = "VERIFICATION"


class Budget(BaseModel):
    max_steps: int = Field(default=12, ge=1, le=100)
    max_capability_calls: int = Field(default=12, ge=1, le=100)
    max_retrieval_rounds: int = Field(default=3, ge=1, le=20)
    max_web_searches: int = Field(default=3, ge=0, le=20)
    max_web_fetches: int = Field(default=5, ge=0, le=50)
    max_verification_rounds: int = Field(default=2, ge=0, le=10)
    max_context_chars: int = Field(default=120_000, ge=1_000, le=1_000_000)


class AnswerConstraints(BaseModel):
    language: str = "bg"
    max_words: int | None = Field(default=150, ge=1, le=10_000)
    require_citations: bool = True
    require_provenance: bool = True


class ConversationMessage(BaseModel):
    role: str
    content: str

class ConversationContext(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
    latest_user_message: str | None = None
    latest_assistant_message: str | None = None

class Task(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    conversation_id: str | None = None
    user_request: str
    normalized_question: str | None = None
    task_type: TaskType = TaskType.UNKNOWN
    required_output: str | None = None
    known_context: list[str] = Field(default_factory=list)
    conversation_context: ConversationContext = Field(default_factory=ConversationContext)
    missing_context: list[str] = Field(default_factory=list)
    allowed_source_classes: list[SourceClass] = Field(
        default_factory=lambda: [SourceClass.CORPORATE]
    )
    sensitivity: str = "INTERNAL"
    requested_freshness: str | None = None
    answer_constraints: AnswerConstraints = Field(
        default_factory=AnswerConstraints
    )
    action_intent: str | None = None
    budget: Budget = Field(default_factory=Budget)
    state: TaskState = TaskState.REQUESTED


class PlanStep(BaseModel):
    step_id: str
    type: str
    capability: CapabilityType | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    budget_cost: int = Field(default=1, ge=0)
    evidence_required: bool = False


class Plan(BaseModel):
    plan_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    steps: list[PlanStep] = Field(default_factory=list)
    current_step: int = 0
    max_steps: int = Field(default=12, ge=1, le=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "PLANNED"


class EvidenceRecord(BaseModel):
    evidence_id: str = Field(min_length=1)
    source_class: SourceClass
    source_id: str
    source_location: str | None = None
    claim: str
    authority: str | None = None
    applicability: str | None = None
    freshness: str | None = None
    access_scope: str | None = None
    version: str | int | None = None
    scope: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    conditions: list[str] = Field(default_factory=list)
    semantic_metric: str | None = None
    retrieval_time: datetime | None = None
    content_hash: str | None = None
    corroboration: list[str] = Field(default_factory=list)
    contradiction: list[str] = Field(default_factory=list)
    trusted_as_instruction: bool = False


class SynthesisClaim(BaseModel):
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)


class SynthesisResult(BaseModel):
    answer: str
    resolution: QuestionResolution = QuestionResolution.ANSWERABLE
    material_claims: list[SynthesisClaim] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None
    uncertainty: str | None = None


class SemanticVerificationItem(BaseModel):
    claim_index: int
    status: str
    reason: str


class VerificationResult(BaseModel):
    passed: bool
    material_claims_checked: int = 0
    unsupported_claims: list[str] = Field(default_factory=list)
    invalid_citations: list[str] = Field(default_factory=list)
    applicability_errors: list[str] = Field(default_factory=list)
    conflict_errors: list[str] = Field(default_factory=list)
    semantic_results: list[SemanticVerificationItem] = Field(
        default_factory=list
    )
    semantic_errors: list[str] = Field(default_factory=list)
    reason: str | None = None


class OrchestrationRequest(BaseModel):
    conversation_id: str | None = None
    user_request: str = Field(min_length=1)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    source_policy: list[SourceClass] = Field(
        default_factory=lambda: [SourceClass.CORPORATE]
    )
    requested_freshness: str | None = None
    output_constraints: AnswerConstraints = Field(
        default_factory=AnswerConstraints
    )
    budget: Budget = Field(default_factory=Budget)
    user_context: dict[str, Any] = Field(default_factory=dict)


class OrchestrationResponse(BaseModel):
    task_id: UUID
    task_type: TaskType
    plan: Plan | None = None
    resolution: QuestionResolution
    answer: str
    answer_status: AnswerStatus
    evidence_status: EvidenceStatus
    citations: list[str] = Field(default_factory=list)
    provenance: list[EvidenceRecord] = Field(default_factory=list)
    clarification: str | None = None
    trace_id: str
    verification: VerificationResult | None = None
    state: TaskState = TaskState.TRACE_COMPLETE
