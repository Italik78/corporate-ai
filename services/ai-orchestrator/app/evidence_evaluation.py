from __future__ import annotations

from pydantic import BaseModel, Field

from .applicability import (
    ApplicabilityStatus,
    evaluate_evidence_applicability,
)
from .models import EvidenceRecord, EvidenceStatus


class EvidenceEvaluationResult(BaseModel):
    status: EvidenceStatus
    applicable: list[EvidenceRecord] = Field(default_factory=list)
    unknown: list[EvidenceRecord] = Field(default_factory=list)
    rejected: list[EvidenceRecord] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


def evaluate_evidence(
    evidence: list[EvidenceRecord],
) -> EvidenceEvaluationResult:
    applicable: list[EvidenceRecord] = []
    unknown: list[EvidenceRecord] = []
    rejected: list[EvidenceRecord] = []
    reasons: list[str] = []

    for item in evidence:
        result = evaluate_evidence_applicability(item)

        if result.status == ApplicabilityStatus.APPLICABLE:
            applicable.append(item)
        elif result.status == ApplicabilityStatus.UNKNOWN:
            unknown.append(item)
        else:
            rejected.append(item)

    if applicable:
        status = EvidenceStatus.SUPPORTED
    elif unknown:
        status = EvidenceStatus.INSUFFICIENT_EVIDENCE
        reasons.append("evidence exists but applicability is not established")
    else:
        status = EvidenceStatus.INSUFFICIENT_EVIDENCE
        reasons.append("no applicable evidence remains")

    return EvidenceEvaluationResult(
        status=status,
        applicable=applicable,
        unknown=unknown,
        rejected=rejected,
        reasons=reasons,
    )
