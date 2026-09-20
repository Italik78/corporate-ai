import json

from app.rag import normalize_source_ids, parse_decision


def test_normalize_source_ids_accepts_numeric_strings_and_deduplicates():
    assert normalize_source_ids([1, "2", "2", 3.0, True, 0, -1, "bad"]) == [1, 2, 3]


def test_parse_decision_normalizes_top_level_and_claim_provenance():
    raw = json.dumps({
        "answerable": True,
        "answer": "Срокът е 5 работни дни.",
        "source_ids": ["1", 1],
        "claims": [
            {
                "text": "Срокът е 5 работни дни.",
                "source_ids": ["1"]
            }
        ],
        "unanswered_parts": []
    })

    decision = parse_decision(raw)

    assert decision["source_ids"] == [1]
    assert decision["claims"][0]["source_ids"] == [1]


def test_parse_decision_applies_top_level_sources_to_string_claims():
    raw = json.dumps({
        "answerable": True,
        "answer": "Отговор.",
        "source_ids": ["1", "2"],
        "claims": ["Подкрепено твърдение."],
        "unanswered_parts": []
    })

    decision = parse_decision(raw)

    assert decision["source_ids"] == [1, 2]
    assert decision["claims"][0]["source_ids"] == [1, 2]
