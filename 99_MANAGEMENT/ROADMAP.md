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
- Document & Knowledge Architecture v1.

### Phase A.2 — Document Metadata & Version Foundation

- [x] PostgreSQL metadata registry
- [x] SHA-256 deduplication
- [x] document versions and lifecycle
- [x] supersession relationships
- [x] effective dates / project / access scope metadata
- [x] metadata propagation to Qdrant
- [x] version/lifecycle filters in Knowledge Engine
- [x] DGX version/lifecycle filter acceptance validation

### Phase B — Office / Tabular Normalization

Implemented:
- [x] DOCX extractor
- [x] XLSX extractor
- [x] PPTX extractor
- [x] CSV extractor
- [x] normalized blocks with table/heading provenance
- [x] pipeline routing to format-specific extractors
- [x] Knowledge Engine handoff through normalized chunks

Pending:
- [ ] DGX build and end-to-end ingestion/RAG validation
- [ ] validate Open WebUI upload integration with Document Ingestion
- [ ] validate production retrieval path without Open WebUI independent file-* vector collections

### Phase C — Open WebUI Integration & Web Search

**Status: ARCHITECTURE DEFINED / VALIDATION PENDING**

Baseline:
- `04_KNOWLEDGE/OPEN_WEBUI_INTEGRATION_AND_WEB_SEARCH.md`

#### C1 — Open WebUI integration discovery
- [ ] validate External Knowledge → Qdrant against `corporate_knowledge`
- [ ] validate query embedding compatibility with Qwen3-Embedding-4B / 2560 dimensions
- [ ] validate metadata/citation mapping
- [ ] validate Knowledge Base behavior
- [ ] validate Filter `file_handler`
- [ ] select the upload integration path
- [ ] prevent duplicate Open WebUI production vector indexing

#### C2 — Controlled document upload
- [ ] route Open WebUI uploads into Document Ingestion
- [ ] preserve existing UI upload experience
- [ ] register metadata/version before indexing
- [ ] preserve original file outside Qdrant
- [ ] validate DOCX/XLSX/PPTX/CSV end-to-end
- [ ] integrate PDF/OCR/Vision

#### C3 — Corporate Knowledge integration
- [ ] expose Corporate Knowledge through validated external Qdrant or Knowledge Engine integration
- [ ] enforce version/lifecycle/project/access filters
- [ ] preserve evidence claims and citations
- [ ] validate current/superseded version behavior in UI

#### C4 — Controlled Web Search
- [ ] decide SearXNG vs hosted provider
- [ ] deploy controlled search egress
- [ ] normalize web evidence
- [ ] implement bounded URL fetching
- [ ] preserve URL and retrieval timestamp provenance
- [ ] add domain/timeout/size/concurrency controls
- [ ] isolate web prompt injection
- [ ] keep LLM network access disabled

#### C5 — Agent integration
- [ ] internal-first/web-fallback policy
- [ ] explicit research workflow
- [ ] cross-source evidence evaluation
- [ ] separate internal/web provenance
- [ ] confirmation for high-impact actions
- [ ] artifact traceability

#### C6 — DGX acceptance
- [ ] UI upload → Document Ingestion → PostgreSQL → Qdrant
- [ ] internal grounded query
- [ ] explicit web query
- [ ] mixed internal + web query
- [ ] citation/provenance verification
- [ ] blocked-domain and prompt-injection tests
- [ ] timeout/resource exhaustion tests
- [ ] internal-only/offline mode

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
