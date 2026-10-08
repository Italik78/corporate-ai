"""Deterministic structured queries over validated document data."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import xlrd

from .models import StructuredFilter, StructuredRowEvidence


def extract_xls_rows(filename: str, data: bytes) -> list[dict[str, Any]]:
    """Extract XLS rows while preserving sheet and row provenance."""
    if Path(filename).suffix.lower() != ".xls":
        raise StructuredQueryError("UNSUPPORTED_STRUCTURED_FORMAT")

    try:
        workbook = xlrd.open_workbook(file_contents=data)
    except Exception as exc:
        raise StructuredQueryError("XLS_PARSE_ERROR") from exc

    result: list[dict[str, Any]] = []

    for sheet_index in range(workbook.nsheets):
        worksheet = workbook.sheet_by_index(sheet_index)

        if worksheet.nrows == 0 or worksheet.ncols == 0:
            continue

        headers = [
            str(worksheet.cell_value(0, col_index)).strip()
            for col_index in range(worksheet.ncols)
        ]

        for row_index in range(1, worksheet.nrows):
            values = [
                worksheet.cell_value(row_index, col_index)
                for col_index in range(worksheet.ncols)
            ]

            if not any(str(value).strip() for value in values):
                continue

            cells: dict[str, Any] = {}

            for col_index, value in enumerate(values):
                header = (
                    headers[col_index]
                    if col_index < len(headers)
                    else ""
                )
                key = header or f"column_{col_index + 1}"
                cells[key] = value

            result.append(
                {
                    "sheet": worksheet.name,
                    "sheet_index": sheet_index + 1,
                    "row_index": row_index + 1,
                    "cells": cells,
                }
            )

    return result


class StructuredQueryError(ValueError):
    """Raised when a structured query cannot be evaluated safely."""


def _parse_date(value: Any) -> date:
    text = str(value).strip()

    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise StructuredQueryError(f"INVALID_DATE_VALUE:{text}")


def _compare(value: Any, query: StructuredFilter) -> bool:
    operator = query.operator
    expected = query.value

    if operator == "contains":
        return expected.casefold() in str(value).casefold()

    if operator == "eq":
        return str(value).strip().casefold() == expected.strip().casefold()

    if operator in {"gte", "lte", "gt", "lt"}:
        left = _parse_date(value)
        right = _parse_date(expected)

        if operator == "gte":
            return left >= right
        if operator == "lte":
            return left <= right
        if operator == "gt":
            return left > right
        if operator == "lt":
            return left < right

    raise StructuredQueryError(f"UNSUPPORTED_OPERATOR:{operator}")


def query_xls_rows_with_count(
    rows: list[dict[str, Any]],
    *,
    sheet: str | None = None,
    filters: list[StructuredFilter] | None = None,
    columns: list[str] | None = None,
    limit: int = 100,
) -> tuple[list[StructuredRowEvidence], int]:
    if limit < 1 or limit > 1000:
        raise StructuredQueryError("INVALID_LIMIT")

    active_filters = filters or []
    result: list[StructuredRowEvidence] = []
    total_matches = 0

    for row in rows:
        if sheet is not None and row["sheet"] != sheet:
            continue

        cells = row["cells"]

        if columns is not None:
            unknown_columns = [
                column for column in columns if column not in cells
            ]
            if unknown_columns:
                raise StructuredQueryError(
                    f"UNKNOWN_COLUMN:{unknown_columns[0]}"
                )

        for query_filter in active_filters:
            if query_filter.column not in cells:
                raise StructuredQueryError(
                    f"UNKNOWN_COLUMN:{query_filter.column}"
                )

            if not _compare(cells[query_filter.column], query_filter):
                break
        else:
            total_matches += 1

            if len(result) < limit:
                selected_cells = (
                    cells
                    if columns is None
                    else {column: cells[column] for column in columns}
                )

                result.append(
                    StructuredRowEvidence(
                        sheet=row["sheet"],
                        sheet_index=row["sheet_index"],
                        row_index=row["row_index"],
                        cells=selected_cells,
                    )
                )

    return result, total_matches


def query_xls_rows(
    rows: list[dict[str, Any]],
    *,
    sheet: str | None = None,
    filters: list[StructuredFilter] | None = None,
    columns: list[str] | None = None,
    limit: int = 100,
) -> list[StructuredRowEvidence]:
    result, _ = query_xls_rows_with_count(
        rows,
        sheet=sheet,
        filters=filters,
        columns=columns,
        limit=limit,
    )
    return result
