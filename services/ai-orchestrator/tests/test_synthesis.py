from app.models import EvidenceRecord, SourceClass, Task
from app.synthesis import build_synthesis_messages


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
