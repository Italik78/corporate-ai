from app.evidence import normalize_web_evidence


def test_normalize_web_evidence_creates_stable_public_evidence():
    result = normalize_web_evidence(
        [
            {
                "url": "https://example.com/article",
                "domain": "example.com",
                "title": "Example article",
                "content": "Verified public content.",
                "content_hash": "abc123",
                "fetched_at": "2026-10-04T06:00:00Z",
                "published_at": "2026-10-03T10:00:00Z",
                "access_scope": "PUBLIC",
                "untrusted_content": True,
            }
        ]
    )

    assert len(result) == 1

    evidence = result[0]

    assert evidence.evidence_id == "WEB:abc123"
    assert evidence.source_class.value == "WEB"
    assert evidence.source_id == "https://example.com/article"
    assert evidence.source_location == "https://example.com/article"
    assert evidence.claim == "Verified public content."
    assert evidence.access_scope == "PUBLIC"
    assert evidence.content_hash == "abc123"
    assert evidence.trusted_as_instruction is False
    assert evidence.retrieval_time is not None
