from app.models import EvidenceRecord, QuestionResolution, SourceClass, Task
from app.synthesis import build_synthesis_messages, parse_synthesis_result


def test_synthesis_context_preserves_source_class_and_web_provenance():
    evidence = [
        EvidenceRecord(
            evidence_id="WEB:abc123",
            source_class=SourceClass.WEB,
            source_id="https://example.com/article",
            source_location="https://example.com/article",
            claim="Verified public content.",
            authority="example.com",
            freshness="2026-10-03T10:00:00+00:00",
            access_scope="PUBLIC",
            content_hash="abc123",
            trusted_as_instruction=False,
        )
    ]

    task = Task(
        user_request="Какво казва публичният източник?"
    )
    messages = build_synthesis_messages(task, evidence)

    prompt = messages[1]["content"]

    assert "source_class: WEB" in prompt
    assert "authority: example.com" in prompt
    assert "freshness: 2026-10-03T10:00:00+00:00" in prompt
    assert "EXACT_EVIDENCE_ID: WEB:abc123" in prompt


def test_conflicted_synthesis_keeps_source_separated_claim_citations():
    evidence = [
        EvidenceRecord(
            evidence_id="CORP:contract-price",
            source_class=SourceClass.CORPORATE,
            source_id="contract-1",
            claim="Contract price: 100 EUR for 36 months.",
            version=1,
        ),
        EvidenceRecord(
            evidence_id="WEB:official-price",
            source_class=SourceClass.WEB,
            source_id="https://www.apis.bg/bg/ceni",
            source_location="https://www.apis.bg/bg/ceni",
            claim="Public price: 120 EUR for 12 months.",
            access_scope="PUBLIC",
        ),
    ]
    result = parse_synthesis_result(
        answer=(
            '{"answer":"The contract is 100 EUR for 36 months; the current public price is '
            '120 EUR for 12 months. These periods differ, so applicability needs review.",'
            '"resolution":"CONFLICTED","material_claims":['
            '{"claim":"Contract price is 100 EUR for 36 months.","evidence_ids":["CORP:contract-price"]},'
            '{"claim":"Official public price is 120 EUR for 12 months.","evidence_ids":["WEB:official-price"]}],'
            '"needs_clarification":false,"clarification_question":null,"uncertainty":null}'
        ),
        evidence=evidence,
    )
    assert result.resolution == QuestionResolution.CONFLICTED
    assert result.evidence_ids == ["CORP:contract-price", "WEB:official-price"]
    assert [claim.evidence_ids for claim in result.material_claims] == [
        ["CORP:contract-price"],
        ["WEB:official-price"],
    ]
