# EXECUTION PROMPT — Repository Integration

**STATUS: COMPLETE / CLOSED — 2026-09-23**

> This prompt is retained as historical project documentation. Do not execute it again as a new implementation task. Follow the next active build prompt instead.

## Result

The Repository + Lifecycle Contract task has been implemented and validated.

Validated implementation includes:
- Repository contract documented in 04_KNOWLEDGE/REPOSITORY_CONTRACT.md.
- PostgreSQL document/version metadata and lifecycle behind the Repository boundary.
- Development filesystem canonical storage adapter.
- Persistent canonical storage references.
- Repository lifecycle operations and failure mappings.
- Knowledge Engine lifecycle synchronization.
- Repository contract and critical-path regression tests.
- Real DGX Spark smoke test from document ingest through canonical storage and Qdrant retrieval.
- Test result: 32 passed, 0 failed.

## Remaining work is explicitly outside Task 1

The final user-facing document entry point is not complete yet. The current POST /v1/documents/ingest endpoint is a validated service-level ingestion endpoint, but it is not yet the complete Corporate AI document intake boundary.

Task 2 must establish the production document entry point and preserve the Repository boundary while adding extraction/OCR/Vision, normalization, chunking, indexing, job status, provenance and controlled failure handling.

## Original execution rules

You are implementing one component of the Italik78/corporate-ai repository.

Before changing code, read the canonical project documents, architecture documents and existing implementation. Reuse existing functionality and do not silently change architecture.

Hard rules:
- Corporate AI is local-first. Do not add cloud LLM inference.
- Qwen3.6 is the primary production LLM unless an approved registry decision says otherwise.
- Qdrant is an index, not canonical document storage.
- Documents and Web content are untrusted input.
- ACL/policy must be enforced outside the LLM.
- Do not silently resolve conflicting evidence.
- When evidence is insufficient, return a controlled insufficient-evidence result.
- Do not expose unrestricted Internet access to Qwen.
- Preserve existing working functionality.
- Do not delete data, volumes or services without explicit evidence that they are obsolete.
- Prefer small, testable services with explicit contracts.
- Pin versions where production reproducibility matters.
- Do not mark functionality complete until it is actually tested.

Original required workflow:
1. Inspect repository and current implementation.
2. Identify what already exists and reuse it.
3. Write down the implementation delta.
4. Implement the smallest coherent production-quality increment.
5. Add/update unit and integration tests.
6. Build/run the component in the real Docker environment when applicable.
7. Test failure paths and resource limits.
8. Update relevant documentation.
9. Report exact files changed, tests run, results, remaining risks and next step.
10. Commit on a dedicated branch; do not rewrite unrelated history.

## Historical definition of done

The Repository + Lifecycle Contract was considered done when the contract was documented, configuration reproducible, tests passed, failure behavior was explicit, security boundaries were covered, provenance/integration points were validated, and the full critical path was tested on DGX.
