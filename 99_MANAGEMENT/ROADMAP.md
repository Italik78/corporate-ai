# ROADMAP

## Phase 1 — Baseline

Verify DGX post-update; inventory containers, images, volumes, networks and configs; preserve existing data.

**Status: COMPLETE**

## Phase 2 — Runtime

Declarative service definitions; Qwen3.6; health checks; resource policies.

**Status: COMPLETE**

## Phase 3 — Knowledge

Embedding; Qdrant; Knowledge Engine; RAG; evidence evaluation; universal ingestion.

**Status: IN PROGRESS**

Completed:
- Qwen3-Embedding-4B production configuration and API validation.
- Qdrant `corporate_knowledge` collection and persistence validation.
- Knowledge Engine with search, ingest, health and end-to-end RAG query.
- Grounded positive query and insufficient-evidence negative query.
- Initial conflict retrieval test.
- Evidence Engine with SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE.
- Evidence claims with source IDs.
- Evidence integration into `/v1/query`.
- Knowledge Engine 0.3.1 test runtime validation.
- Normalized RAG response contract.
- Git hygiene for runtime data and backup files.

Architecture baseline added:
- `04_KNOWLEDGE/DOCUMENT_AND_KNOWLEDGE_ARCHITECTURE.md`
- Large documents are not normally placed whole into the LLM context.
- Normalized structure, versioning, document relationships, scoped retrieval and bounded whole-document analysis are defined.

Current limitation:
- Conflict detection is a numeric candidate detector, not a final semantic conflict resolver.
- Retrieval quality and reranking remain separate tasks.
- `/v1/ingest` accepts normalized content; universal file ingestion is not implemented there.

Next:
1. Document Ingestion Service.
2. Implement normalized document model and structure-aware chunking.
3. TXT/Markdown end-to-end ingestion.
4. SHA-256 deduplication/version foundation.
5. Knowledge Engine integration.
6. End-to-end ingestion/RAG test.
7. DOCX/XLSX/PPTX/CSV.
8. PDF/OCR/Vision integration.
9. Object Storage + metadata lifecycle.
10. Permission-aware retrieval.
11. Reranking/evidence fusion.
12. Agent document-analysis workflows.
13. Claims/provenance completion.
14. Partial-answer handling.
15. Conditional reranking/evidence fusion.
16. Improve semantic conflict detection.
17. Evaluate knowledge graph for procedural/organizational relationships.

## Phase 4 — Multimodal

Vision; PDF/image pipeline; structured extraction.

**Status: FOUNDATION VALIDATED / INTEGRATION IN PROGRESS**

Completed:
- PDF classifier/router/preprocessor pipeline prototypes.
- Qwen3.6 Vision API validation.
- Structured Vision JSON validation.
- TABLE, VISUAL and COMPLEX page handling.

Next:
- Integrate PDF/OCR/Vision into Document Ingestion Service.
- Ground visual/table extraction into Knowledge Engine.
- Propagate confidence and uncertainty.

## Phase 5 — Agent

Gateway; tool policy; Office tools; approval workflow; document lifecycle.

**Status: FOUNDATION / NOT YET INTEGRATED**

Target:
- Agent Controller.
- Tool Policy and schema validation.
- Office Tool Gateway.
- Preview-before-side-effect workflow.
- Word/Excel/PowerPoint/PDF generation and reading.
- Traceability matrix and provenance.

## Phase 6 — UI

Open WebUI/Pipe; streaming/status events; Corporate AI Console.

**Status: FOUNDATION**

- Open WebUI selected as primary interaction layer.
- Corporate AI Console defined for infrastructure/application status.
- Avoid a parallel custom chat UI.

## Phase 7 — Production

Security; backups; recovery; evaluation; observability; performance/resource tuning.

**Status: NOT COMPLETE**

Focus:
- secret management and tool authentication.
- backup/recovery validation.
- evaluation suite.
- observability.
- resource contention tests.
- security hardening.
- deployment reproducibility.


### Phase A.2 — Document Metadata & Version Foundation
- [x] PostgreSQL metadata registry
- [x] SHA-256 deduplication
- [x] document versions and lifecycle
- [x] supersession relationships
- [x] effective dates / project / access scope metadata
- [x] metadata propagation to Qdrant
- [x] version/lifecycle filters in Knowledge Engine
- [ ] DGX integration and end-to-end version transition validation
