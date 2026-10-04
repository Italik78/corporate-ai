from __future__ import annotations

from .models import EvidenceRecord, SynthesisClaim, VerificationResult


def verify_evidence_support(
    *,
    claims: list[SynthesisClaim],
    evidence: list[EvidenceRecord],
    citations: list[str],
    applicability_errors: list[str] | None = None,
    conflict_errors: list[str] | None = None,
) -> VerificationResult:
    applicability_errors = applicability_errors or []
    conflict_errors = conflict_errors or []

    unsupported_claims: list[str] = []
    invalid_citations: list[str] = []

    evidence_ids = {item.evidence_id for item in evidence}

    for claim in claims:
        if not claim.evidence_ids:
            unsupported_claims.append(
                f"Material claim has no evidence: {claim.claim}"
            )
            continue

        for evidence_id in claim.evidence_ids:
            if evidence_id not in evidence_ids:
                invalid_citations.append(evidence_id)

    for citation in citations:
        if citation not in evidence_ids:
            invalid_citations.append(citation)

    invalid_citations = list(dict.fromkeys(invalid_citations))

    passed = not (
        unsupported_claims
        or invalid_citations
        or applicability_errors
        or conflict_errors
    )

    return VerificationResult(
        passed=passed,
        material_claims_checked=len(claims),
        unsupported_claims=unsupported_claims,
        invalid_citations=invalid_citations,
        applicability_errors=applicability_errors,
        conflict_errors=conflict_errors,
        reason=(
            "Evidence traceability checks passed."
            if passed
            else "One or more evidence traceability checks failed."
        ),
    )
