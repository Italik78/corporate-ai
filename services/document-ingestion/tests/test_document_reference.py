from app.document_reference import (
    DocumentReferenceStatus,
    resolve_document_reference,
)
from app.models import DocumentVersionResponse, LifecycleStatus


def make_document(source_file: str, document_id: str) -> DocumentVersionResponse:
    return DocumentVersionResponse(
        document_id=document_id,
        version=1,
        source_file=source_file,
        content_hash=f"hash-{document_id}",
        source_system="upload",
        source_reference=None,
        title=source_file.rsplit(".", 1)[0],
        author=None,
        classification="INTERNAL",
        language="bg",
        document_date=None,
        effective_from=None,
        effective_to=None,
        lifecycle_status=LifecycleStatus.CURRENT,
        parent_document_id=None,
        supersedes=None,
        superseded_by=None,
        project_id=None,
        access_scope="INTERNAL",
        canonical_storage_key=None,
        created_at="2026-10-06T00:00:00+00:00",
        updated_at="2026-10-06T00:00:00+00:00",
    )


DOCUMENTS = [
    make_document(
        "DfQueryToExcel (6).xls",
        "doc-6",
    ),
    make_document(
        "DfQueryToExcel (7.1).xls",
        "doc-7-1",
    ),
]


def test_exact_filename_resolves():
    result = resolve_document_reference(
        "DfQueryToExcel (7.1).xls",
        DOCUMENTS,
    )

    assert result.status == DocumentReferenceStatus.RESOLVED
    assert result.document is not None
    assert result.document.document_id == "doc-7-1"


def test_exact_stem_resolves():
    documents = [
        make_document(
            "DfQueryToExcel.xlsx",
            "doc-xlsx",
        )
    ]

    result = resolve_document_reference(
        "DfQueryToExcel",
        documents,
    )

    assert result.status == DocumentReferenceStatus.RESOLVED
    assert result.document is not None
    assert result.document.document_id == "doc-xlsx"


def test_copy_family_is_ambiguous():
    result = resolve_document_reference(
        "DfQueryToExcel",
        DOCUMENTS,
    )

    assert result.status == DocumentReferenceStatus.AMBIGUOUS
    assert {item.document_id for item in result.matches} == {
        "doc-6",
        "doc-7-1",
    }


def test_unknown_reference_is_not_found():
    result = resolve_document_reference(
        "DoesNotExist",
        DOCUMENTS,
    )

    assert result.status == DocumentReferenceStatus.NOT_FOUND
    assert result.document is None
    assert result.matches == []


def test_no_fuzzy_matching():
    documents = [
        make_document(
            "DfQueryToExcelFinal.xls",
            "doc-final",
        )
    ]

    result = resolve_document_reference(
        "DfQueryToExcel",
        documents,
    )

    assert result.status == DocumentReferenceStatus.NOT_FOUND
