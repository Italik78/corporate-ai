from __future__ import annotations

from enum import Enum
from pathlib import Path
import re

from .models import DocumentVersionResponse


class DocumentReferenceStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


class DocumentReferenceResolution:
    def __init__(
        self,
        status: DocumentReferenceStatus,
        document: DocumentVersionResponse | None = None,
        matches: list[DocumentVersionResponse] | None = None,
    ) -> None:
        self.status = status
        self.document = document
        self.matches = matches or []


_COPY_SUFFIX_RE = re.compile(r"^(?P<base>.+?) \([^()]+\)$")


def resolve_document_reference(
    reference: str,
    documents: list[DocumentVersionResponse],
) -> DocumentReferenceResolution:
    normalized = reference.strip()
    if not normalized:
        return DocumentReferenceResolution(DocumentReferenceStatus.NOT_FOUND)

    # 1. Exact source_file match.
    exact = [
        document
        for document in documents
        if document.source_file == normalized
    ]
    if len(exact) == 1:
        return DocumentReferenceResolution(
            DocumentReferenceStatus.RESOLVED,
            document=exact[0],
        )
    if len(exact) > 1:
        return DocumentReferenceResolution(
            DocumentReferenceStatus.AMBIGUOUS,
            matches=exact,
        )

    # 2. Exact filename stem match.
    stem_matches = [
        document
        for document in documents
        if Path(document.source_file).stem == normalized
    ]
    if len(stem_matches) == 1:
        return DocumentReferenceResolution(
            DocumentReferenceStatus.RESOLVED,
            document=stem_matches[0],
        )
    if len(stem_matches) > 1:
        return DocumentReferenceResolution(
            DocumentReferenceStatus.AMBIGUOUS,
            matches=stem_matches,
        )

    # 3. Controlled copy/version family match.
    family_matches = []
    for document in documents:
        stem = Path(document.source_file).stem
        match = _COPY_SUFFIX_RE.match(stem)
        if match and match.group("base") == normalized:
            family_matches.append(document)

    if len(family_matches) == 1:
        return DocumentReferenceResolution(
            DocumentReferenceStatus.RESOLVED,
            document=family_matches[0],
        )
    if len(family_matches) > 1:
        return DocumentReferenceResolution(
            DocumentReferenceStatus.AMBIGUOUS,
            matches=family_matches,
        )

    return DocumentReferenceResolution(DocumentReferenceStatus.NOT_FOUND)
