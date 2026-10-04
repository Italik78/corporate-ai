from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .models import EvidenceRecord


class ConflictType(str, Enum):
    SEMANTIC_CONFLICT = "SEMANTIC_CONFLICT"
    SCOPE_CONFLICT = "SCOPE_CONFLICT"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    EFFECTIVE_DATE_CONFLICT = "EFFECTIVE_DATE_CONFLICT"
    CONDITION_CONFLICT = "CONDITION_CONFLICT"
    METRIC_DIFFERENCE = "METRIC_DIFFERENCE"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"


class ConflictRecord(BaseModel):
    conflict_id: str
    conflict_type: ConflictType
    evidence_ids: list[str] = Field(min_length=2)
    description: str


class ConflictAnalysisResult(BaseModel):
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    unresolved: bool = False
    reason: str | None = None


def analyze_conflicts(
    evidence: list[EvidenceRecord],
) -> ConflictAnalysisResult:
    conflicts: list[ConflictRecord] = []

    for index, left in enumerate(evidence):
        for right in evidence[index + 1:]:
            if (
                left.scope
                and right.scope
                and left.scope != right.scope
                and left.semantic_metric
                and right.semantic_metric
                and left.semantic_metric == right.semantic_metric
            ):
                conflicts.append(
                    ConflictRecord(
                        conflict_id=f"{left.evidence_id}:{right.evidence_id}:scope",
                        conflict_type=ConflictType.SCOPE_CONFLICT,
                        evidence_ids=[left.evidence_id, right.evidence_id],
                        description=(
                            "Evidence records use different explicit scopes "
                            "for the same semantic metric."
                        ),
                    )
                )

    return ConflictAnalysisResult(
        conflicts=conflicts,
        unresolved=bool(conflicts),
        reason=(
            "Explicit scope conflict candidates detected."
            if conflicts
            else "No metadata-level conflict detected."
        ),
    )
