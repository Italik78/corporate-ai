# Corporate AI — Task Status

**Updated:** 2026-09-23

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

**Status: NEXT / IN PROGRESS**

The ingestion foundation exists, but the project does not yet have the final user-facing document entry point.

Current validated technical entry point:
- POST /v1/documents/ingest on Document Ingestion.

This is currently a service-level API used for runtime validation, not yet the complete Corporate AI document intake boundary.

Task 2 must therefore establish the production document entry point and route it through:
1. request validation/security intake;
2. Repository document registration and canonical storage;
3. extraction/OCR/Vision by document type;
4. normalization and chunking;
5. Knowledge Engine indexing;
6. lifecycle/provenance synchronization;
7. deterministic job/status reporting;
8. controlled failure and cleanup semantics.

The entry point must support the target document intake architecture without bypassing the Repository boundary.

## Completion rule

A task is not marked complete from documentation alone. Completion requires code, tests and real runtime validation.

Completed tasks should remain visible in project history/status rather than being silently deleted.
