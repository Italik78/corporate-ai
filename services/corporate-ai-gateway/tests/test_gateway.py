import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import (
    VERSION,
    heuristic_route,
    latest_user_message,
    metadata_from_rag,
    source_context,
    valid_source_citations,
    routing_context,
)


def test_version():
    assert VERSION == "0.3.1"


def test_internal_question_routes_to_rag():
    assert heuristic_route("Какъв е размерът на дневните командировъчни?") == "rag"


def test_general_question_is_not_forced_by_heuristic():
    assert heuristic_route("Как работи Docker контейнер?") is None


def test_latest_user_message_ignores_assistant():
    messages = [
        {"role": "user", "content": "първи въпрос"},
        {"role": "assistant", "content": "отговор"},
        {"role": "user", "content": "втори въпрос"},
    ]
    assert latest_user_message(messages) == "втори въпрос"


def test_source_context_contains_provenance():
    context = source_context([{
        "document_id": "doc-1",
        "source_file": "policy.md",
        "page": 3,
        "score": 0.81,
        "content": "Дневните са 40 EUR.",
    }])
    assert "[SOURCE 1]" in context
    assert "document_id: doc-1" in context
    assert "source_file: policy.md" in context
    assert "page: 3" in context
    assert "Дневните са 40 EUR." in context


def test_metadata_preserves_evidence():
    result = {
        "grounded": True,
        "answer_status": "SUPPORTED",
        "evidence_status": "SUPPORTED",
        "evidence_claims": [{"type": "supported"}],
        "evidence_reason": "ok",
        "sources": [{"document_id": "doc-1"}],
    }
    metadata = metadata_from_rag(result, "deterministic_domain_match")
    assert metadata["gateway_version"] == "0.3.1"
    assert metadata["route"] == "rag"
    assert metadata["grounded"] is True
    assert metadata["evidence_status"] == "SUPPORTED"
    assert metadata["sources"][0]["document_id"] == "doc-1"


def test_citation_validation_rejects_missing_citations():
    assert not valid_source_citations("Отговор без източник.", 2)


def test_citation_validation_rejects_unknown_source():
    assert not valid_source_citations("Твърдение [3].", 2)


def test_citation_validation_accepts_known_source():
    assert valid_source_citations("Твърдение [1].", 2)


def test_routing_context_uses_user_turns_only():
    messages = [
        type("M", (), {"role": "user", "content": "Каква е нашата политика за отпуските?"})(),
        type("M", (), {"role": "assistant", "content": "Измислен асистентски отговор."})(),
        type("M", (), {"role": "user", "content": "А при нас как е?"})(),
    ]
    context = routing_context(messages, "А при нас как е?")
    assert "нашата политика" in context
    assert "А при нас как е?" in context
    assert "Измислен асистентски отговор" not in context
