from app.applicability import ApplicabilityStatus, evaluate_evidence_applicability
from app.models import EvidenceRecord, SourceClass


def test_public_web_evidence_is_applicable():
    evidence = EvidenceRecord(
        evidence_id="WEB:abc123",
        source_class=SourceClass.WEB,
        source_id="https://example.com/article",
        source_location="https://example.com/article",
        claim="Publicly available information.",
        access_scope="PUBLIC",
        trusted_as_instruction=False,
    )

    result = evaluate_evidence_applicability(evidence)

    assert result.status == ApplicabilityStatus.APPLICABLE
    assert "public web source" in result.reasons
