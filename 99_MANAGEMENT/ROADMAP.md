# ROADMAP

## Phase 1 — Baseline
Verify DGX post-update; inventory containers, images, volumes, networks and configs; preserve existing data.

**Status: COMPLETE**

## Phase 2 — Runtime
Declarative service definitions; Qwen3.6; health checks; resource policies.

**Status: COMPLETE**

## Phase 3 — Knowledge
Embedding; Qdrant; reranker; universal ingestion; RAG; evidence evaluation; graph evaluation.

**Status: IN PROGRESS**

Completed:
- Qwen3-Embedding-4B production configuration and API validation.
- Qdrant production collection and persistence validation.
- Knowledge Engine v0.x with search, ingest, health and end-to-end RAG query.
- Grounded positive query and insufficient-evidence negative query.
- Initial conflict retrieval test.

Next:
1. Evidence Engine v0.1 as a separate module.
2. Explicit statuses: SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE.
3. Evidence claims with source IDs and provenance.
4. Integrate Evidence Engine into `/v1/query`.
5. Add partial-answer handling for mixed questions.
6. Conditional reranking and evidence fusion.
7. Evaluate knowledge graph for procedural/organizational relationships.

## Phase 4 — Multimodal
Vision; PDF/image pipeline; structured extraction.

**Status: FOUNDATION VALIDATED / INTEGRATION IN PROGRESS**

Completed:
- PDF classifier/router/preprocessor pipeline prototypes.
- Qwen3.6 vision API validation.
- Production vision JSON Schema validation.
- Test images and page-type classification available.

Next:
- Integrate document intelligence into universal ingestion.
- Ground visual/table extraction into Knowledge Engine.
- Add confidence and uncertainty propagation.

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
