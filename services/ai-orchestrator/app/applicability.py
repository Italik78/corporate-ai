from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .models import EvidenceRecord


class ApplicabilityStatus(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class ApplicabilityResult(BaseModel):
    evidence_id: str
    status: ApplicabilityStatus
    reasons: list[str] = Field(default_factory=list)


def evaluate_evidence_applicability(
    evidence: EvidenceRecord,
    *,
    as_of: datetime | None = None,
) -> ApplicabilityResult:
    now = as_of or datetime.now().astimezone()
    reasons: list[str] = []

    if (
        evidence.source_class.value == "WEB"
        and evidence.access_scope == "PUBLIC"
    ):
        reasons.append("public web source")

    if evidence.effective_from is not None and now < evidence.effective_from:
        return ApplicabilityResult(
            evidence_id=evidence.evidence_id,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reasons=["evidence is not yet effective"],
        )

    if evidence.effective_to is not None and now > evidence.effective_to:
        return ApplicabilityResult(
            evidence_id=evidence.evidence_id,
            status=ApplicabilityStatus.NOT_APPLICABLE,
            reasons=["evidence is no longer effective"],
        )

    if evidence.scope:
        reasons.append("scope metadata is present")

    if evidence.version is not None:
        reasons.append("version metadata is present")

    if evidence.effective_from is not None or evidence.effective_to is not None:
        reasons.append("effective-date metadata is present")

    if not reasons:
        return ApplicabilityResult(
            evidence_id=evidence.evidence_id,
            status=ApplicabilityStatus.UNKNOWN,
            reasons=["insufficient applicability metadata"],
        )

    return ApplicabilityResult(
        evidence_id=evidence.evidence_id,
        status=ApplicabilityStatus.APPLICABLE,
        reasons=reasons,
    )
