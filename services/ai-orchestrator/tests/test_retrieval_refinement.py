from app.retrieval_refinement import parse_refinement_result


def test_parse_refinement_result_normalizes_json_null():
    result = parse_refinement_result(
        '{"query": null, "reason": "ambiguous"}'
    )

    assert result.query is None


def test_parse_refinement_result_normalizes_string_null():
    result = parse_refinement_result(
        '{"query": "null", "reason": "ambiguous"}'
    )

    assert result.query is None


def test_parse_refinement_result_normalizes_whitespace_string_null():
    result = parse_refinement_result(
        '{"query": "  null  ", "reason": "ambiguous"}'
    )

    assert result.query is None


def test_parse_refinement_result_preserves_valid_query():
    result = parse_refinement_result(
        '{"query": "договор A202300905", "reason": "add contract identifier"}'
    )

    assert result.query == "договор A202300905"
