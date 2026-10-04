from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import EvidenceRecord, SourceClass


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    return None


def normalize_corporate_evidence(
    results: list[dict[str, Any]],
) -> list[EvidenceRecord]:
    evidence: list[EvidenceRecord] = []

    for item in results:
        evidence_id = item.get("evidence_id")
        source_id = item.get("source_id")
        claim = item.get("claim")

        if not evidence_id or not source_id or not claim:
            continue

        evidence.append(
            EvidenceRecord(
                evidence_id=str(evidence_id),
                source_class=SourceClass.CORPORATE,
                source_id=str(source_id),
                source_location=(
                    f"{item.get('source_location')}#page={item.get('page')}"
                    if item.get("source_location") and item.get("page") is not None
                    else item.get("source_location")
                ),
                claim=str(claim),
                access_scope=item.get("access_scope"),
                version=item.get("version"),
                effective_from=_parse_datetime(item.get("effective_from")),
                effective_to=_parse_datetime(item.get("effective_to")),
                retrieval_time=datetime.now().astimezone(),
            )
        )

    return evidence


def normalize_web_evidence(
    results: list[dict[str, Any]],
) -> list[EvidenceRecord]:
    evidence: list[EvidenceRecord] = []

    for item in results:
        url = item.get("url")
        content = item.get("content")

        if not isinstance(url, str) or not url.strip():
            continue
        if not isinstance(content, str) or not content.strip():
            continue

        content_hash = item.get("content_hash")
        if isinstance(content_hash, str) and content_hash.strip():
            evidence_id = f"WEB:{content_hash.strip()}"
        else:
            evidence_id = f"WEB:{url.strip()}"

        fetched_at = _parse_datetime(item.get("fetched_at"))
        published_at = _parse_datetime(item.get("published_at"))

        evidence.append(
            EvidenceRecord(
                evidence_id=evidence_id,
                source_class=SourceClass.WEB,
                source_id=url.strip(),
                source_location=url.strip(),
                claim=content.strip(),
                access_scope=item.get("access_scope", "PUBLIC"),
                retrieval_time=fetched_at or datetime.now().astimezone(),
                content_hash=(
                    content_hash.strip()
                    if isinstance(content_hash, str) and content_hash.strip()
                    else None
                ),
                freshness=(
                    published_at.isoformat()
                    if published_at is not None
                    else None
                ),
                trusted_as_instruction=False,
            )
        )

    return evidence
