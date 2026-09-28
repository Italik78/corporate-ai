# Corporate AI — Task Status

**Updated:** 2026-09-28

## Task 1 — Repository + Lifecycle Contract

**Status: COMPLETE / VALIDATED**

The Repository + Lifecycle task is closed. The implementation was validated on the DGX Spark runtime.

Validated:
- Repository boundary is documented in 04_KNOWLEDGE/REPOSITORY_CONTRACT.md.
- PostgreSQL remains authoritative for document/version metadata and lifecycle.
- Canonical source files are stored outside Qdrant.
- Canonical storage references are persisted.
- Lifecycle is propagated from Repository to Knowledge Engine/Qdrant.
- Versioning and SHA-256 duplicate handling remain intact.
- Repository adapter contract and failure mappings are covered by tests.
- Repository → canonical storage → Knowledge Engine critical path is covered by regression testing.
- Real document ingest smoke test reached READY with lifecycle CURRENT.
- Canonical source was verified on disk, metadata in PostgreSQL, and retrieval in Qdrant.
- Test suite result: 32 passed, 0 failed.

### Important architectural clarification

The lifecycle is not duplicated in Knowledge Engine. Repository metadata is authoritative; Knowledge Engine mirrors lifecycle state into its index.

The Repository Contract v0.1 deliberately does not select or deploy Mayan/MinIO yet.

## Task 2 — Universal Document Ingestion

**Status: IMPLEMENTATION FOUNDATION COMPLETE / RUNTIME ACCEPTANCE PENDING**

The production-oriented Document Ingestion entry points and orchestration foundation are implemented. Full Task 2 acceptance is not yet closed because Open WebUI routing and complete DGX acceptance still remain.

Implemented and validated in code/tests:
- POST /v1/documents/ingest as the primary multipart document entry point.
- POST /v1/documents/process as a document-processing entry point returning the normalized document.
- POST /v1/integrations/paperless/webhook as the controlled Paperless boundary.
- Persistent ingestion job metadata in PostgreSQL with status, lifecycle, version and error fields.
- Bounded upload staging with SHA-256 hashing and extension/size validation.
- Repository registration before Knowledge Engine indexing.
- Canonical source storage and canonical storage key persistence.
- Normalized extraction for TXT, Markdown, CSV, DOCX, XLSX, PPTX and native PDF text.
- Versioning, SHA-256 deduplication, lifecycle and supersession handling.
- Project and access-scope metadata propagation.
- `source_reference` support in document metadata, PostgreSQL version records and ingestion paths.
- Paperless source namespace `paperless:{document_id}`.
- Duplicate reconstruction from the authoritative indexed chunks with metadata/provenance preserved.
- Controlled duplicate behavior without re-indexing the same content.
- Unit regression suite: 24 passed, 0 failed.
- Source-reference compile checks: models, metadata and pipeline compile successfully.

Latest validation checkpoint:
- `services/document-ingestion/tests/test_unit.py`: 24 passed, 0 failed, 6 warnings.
- The remaining warnings are PyMuPDF deprecation warnings and pytest cache permission warnings. They do not fail the suite.

Remaining for Task 2 acceptance:
1. Real DGX runtime validation of the current source-reference changes.
2. Open WebUI upload → Document Ingestion routing.
3. Validation that Open WebUI does not create independent `file-*` production collections.
4. Complete end-to-end acceptance including PostgreSQL → canonical storage → Knowledge Engine/Qdrant.
5. PDF OCR/Vision integration for scanned/complex pages.

## Completion rule

A task is not marked complete from documentation alone. Completion requires code, tests and real runtime validation.

Completed tasks should remain visible in project history/status rather than being silently deleted.
