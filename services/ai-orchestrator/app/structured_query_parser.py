from __future__ import annotations

import re
from typing import Any


_FILE_RE = re.compile(
    r"(?P<file>[A-Za-zА-Яа-я0-9_№() .-]+\.(?:xls|xlsx|csv))",
    re.IGNORECASE,
)

_COLUMN_RANGE_RE = re.compile(
    r"колоната\s+(?P<column>[A-Za-zА-Яа-я0-9_№]+)"
    r"\s+е\s+между\s+"
    r"(?P<start>\d{2}\.\d{2}\.\d{4})"
    r"\s+и\s+"
    r"(?P<end>\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)

_COLUMN_UNTIL_RE = re.compile(
    r"колоната\s+(?P<column>[A-Za-zА-Яа-я0-9_№]+)"
    r"(?:\s+е)?\s+до\s+"
    r"(?P<end>\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)

_KRAINA_DATE_RE = re.compile(
    r"крайна\s+дата\s+до\s+"
    r"(?P<end>\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)


def parse_structured_query(user_request: str) -> dict[str, Any] | None:
    """
    Parse only unambiguous structured-document query constructs.

    Returns None when the request is not sufficiently explicit for a
    deterministic structured query. Never invents document IDs, sheets,
    columns, rows, or other metadata.
    """
    text = " ".join(user_request.split())
    if not text:
        return None

    file_match = _FILE_RE.search(text)
    if not file_match:
        return None

    lower = text.casefold()
    structured_context = any(
        marker in lower
        for marker in (
            "файл",
            "файла",
            "таблица",
            "таблицата",
            "редовете",
            "записите",
            "договорите",
            "договорите, при",
        )
    )
    if not structured_context:
        return None

    payload: dict[str, Any] = {
        "source_file": file_match.group("file"),
    }

    range_match = _COLUMN_RANGE_RE.search(text)
    if range_match:
        payload["filters"] = [
            {
                "column": range_match.group("column"),
                "operator": "gte",
                "value": range_match.group("start"),
            },
            {
                "column": range_match.group("column"),
                "operator": "lte",
                "value": range_match.group("end"),
            },
        ]
        return payload

    until_match = _COLUMN_UNTIL_RE.search(text)
    if until_match:
        payload["filters"] = [
            {
                "column": until_match.group("column"),
                "operator": "lte",
                "value": until_match.group("end"),
            }
        ]
        return payload

    krajna_match = _KRAINA_DATE_RE.search(text)
    if krajna_match:
        payload["filters"] = [
            {
                "column": "Край",
                "operator": "lte",
                "value": krajna_match.group("end"),
            }
        ]
        return payload

    return payload
