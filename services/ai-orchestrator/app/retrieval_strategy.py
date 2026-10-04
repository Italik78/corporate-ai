from __future__ import annotations

from collections import defaultdict
from typing import Any


def diversify_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_chunks_per_document: int,
    max_documents: int,
) -> list[dict[str, Any]]:
    if max_chunks_per_document < 1:
        raise ValueError("max_chunks_per_document must be >= 1")
    if max_documents < 1:
        raise ValueError("max_documents must be >= 1")

    selected: list[dict[str, Any]] = []
    chunks_by_document: dict[str, int] = defaultdict(int)
    documents: set[str] = set()

    for candidate in candidates:
        document_id = candidate.get("document_id") or candidate.get("source_id")
        if not document_id:
            continue

        if document_id not in documents:
            if len(documents) >= max_documents:
                continue
            documents.add(document_id)

        if chunks_by_document[document_id] >= max_chunks_per_document:
            continue

        selected.append(candidate)
        chunks_by_document[document_id] += 1

    return selected


from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalStrategy:
    candidate_limit: int = 50
    max_documents: int = 20
    max_chunks_per_document: int = 2
    score_threshold: float = 0.45

    def __post_init__(self) -> None:
        if self.candidate_limit < 1:
            raise ValueError("candidate_limit must be >= 1")
        if self.max_documents < 1:
            raise ValueError("max_documents must be >= 1")
        if self.max_chunks_per_document < 1:
            raise ValueError("max_chunks_per_document must be >= 1")
        if not 0.0 <= self.score_threshold <= 1.0:
            raise ValueError("score_threshold must be between 0 and 1")

def merge_unique_candidates(
    existing: list[dict[str, Any]],
    new_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = {
        str(item["evidence_id"])
        for item in existing
        if item.get("evidence_id")
    }

    merged = list(existing)

    for candidate in new_candidates:
        evidence_id = candidate.get("evidence_id")
        if not evidence_id:
            continue

        evidence_id = str(evidence_id)
        if evidence_id in seen:
            continue

        seen.add(evidence_id)
        merged.append(candidate)

    return merged
