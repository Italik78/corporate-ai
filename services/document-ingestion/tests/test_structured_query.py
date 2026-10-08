from pathlib import Path

import pytest
from app.models import StructuredFilter
from app.structured_query import (
    StructuredQueryError,
    extract_xls_rows,
    query_xls_rows,
    query_xls_rows_with_count,
)


def _xls_bytes() -> bytes:
    fixture = Path(__file__).parent / "fixtures" / "structured_query_fixture.xls"
    return fixture.read_bytes()


def test_extract_xls_rows_preserves_provenance():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    assert len(rows) == 3
    assert rows[0]["sheet"] == "structured_query_fixture"
    assert rows[0]["sheet_index"] == 1
    assert rows[0]["row_index"] == 2
    assert rows[0]["cells"]["Имя"] == "A202600001-000-00"


def test_date_range_query_is_deterministic():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    result = query_xls_rows(
        rows,
        filters=[
            StructuredFilter(
                column="Край",
                operator="gte",
                value="01.12.2026",
            ),
            StructuredFilter(
                column="Край",
                operator="lte",
                value="31.12.2026",
            ),
        ],
        columns=["Имя", "Край"],
    )

    assert len(result) == 1
    assert result[0].row_index == 3
    assert result[0].cells == {
        "Имя": "A202600002-000-00",
        "Край": "31.12.2026",
    }


def test_contains_filter():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    result = query_xls_rows(
        rows,
        filters=[
            StructuredFilter(
                column="Описание",
                operator="contains",
                value="beta",
            )
        ],
    )

    assert len(result) == 1
    assert result[0].cells["Имя"] == "A202600002-000-00"


def test_unknown_column_fails_closed():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    with pytest.raises(StructuredQueryError, match="UNKNOWN_COLUMN"):
        query_xls_rows(
            rows,
            filters=[
                StructuredFilter(
                    column="Несъществуваща колона",
                    operator="eq",
                    value="x",
                )
            ],
        )


def test_unsupported_format_fails_closed():
    with pytest.raises(
        StructuredQueryError,
        match="UNSUPPORTED_STRUCTURED_FORMAT",
    ):
        extract_xls_rows("contracts.xlsx", _xls_bytes())


def test_invalid_date_fails_closed():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    with pytest.raises(
        StructuredQueryError,
        match="INVALID_DATE_VALUE",
    ):
        query_xls_rows(
            rows,
            filters=[
                StructuredFilter(
                    column="Край",
                    operator="gte",
                    value="not-a-date",
                )
            ],
        )


def test_total_matches_is_not_limited_by_result_limit():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    result, total_matches = query_xls_rows_with_count(
        rows,
        filters=[
            StructuredFilter(
                column="Статус",
                operator="eq",
                value="В изпълнение",
            )
        ],
        limit=1,
    )

    assert len(result) == 1
    assert total_matches == 2


def test_unknown_output_column_fails_closed():
    rows = extract_xls_rows("contracts.xls", _xls_bytes())

    with pytest.raises(StructuredQueryError, match="UNKNOWN_COLUMN"):
        query_xls_rows_with_count(
            rows,
            columns=["Имя", "Несъществуваща колона"],
        )
