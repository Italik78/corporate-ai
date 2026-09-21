# ROADMAP

## Corporate Information System — Target

Corporate AI is being built as a **corporate information system**, not only as a chat interface or RAG demo.

The target user experience is Open WebUI, while Corporate AI remains authoritative for document intelligence, knowledge, evidence, business tools, security and provenance.

Core capabilities:

- understand and index shared corporate documents;
- preserve document structure, versions and relationships;
- answer grounded questions with evidence and citations;
- analyze complete documents through bounded, planned workflows;
- compare documents and detect contradictions without silently choosing a winner;
- use Open WebUI folders/workspaces, Knowledge, system prompts, models, skills, tools and web search where appropriate;
- generate Word/Excel/PowerPoint/PDF artifacts with traceability;
- perform controlled Web Research without giving the LLM unrestricted Internet access;
- enforce access scope, lifecycle, tool policy and provenance outside the UI;
- provide internal-only, explicit-web and internal-first/web-fallback operating modes.

Implementation rule:

> Work **command by command on the DGX**, validate every milestone on the real runtime, and only then mark the corresponding roadmap item complete. Documentation or code committed to GitHub is not acceptance by itself.

## Execution protocol

Every implementation step follows:

1. Inspect current state.
2. Change one bounded component.
3. Build/restart only the required service.
4. Run health/API/unit tests.
5. Run an end-to-end test when applicable.
6. Inspect logs and persisted data.
7. Record the result in GitHub.
8. Proceed to the next command.

No destructive cleanup is allowed while an older validated path is still required for comparison.

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
- [x] DGX build and end-to-end ingestion/RAG validation
- [x] PDF native extraction with page/block/bbox provenance
- [x] Paperless-ngx webhook integration
- [x] Tika 3.3.1 + Gotenberg Office conversion path
- [x] TXT/DOCX/XLSX Paperless → Document Ingestion → Qdrant/Knowledge Engine validation
- [ ] validate Open WebUI upload integration with Document Ingestion
- [ ] validate production retrieval path without Open WebUI independent file-* vector collections

### Phase C — Open WebUI Integration & Web Search

**Status: ARCHITECTURE DEFINED / VALIDATION PENDING**

Baseline:
- `04_KNOWLEDGE/OPEN_WEBUI_INTEGRATION_AND_WEB_SEARCH.md`

#### C1 — Open WebUI capability and integration validation
- [ ] confirm installed Open WebUI version and enabled capabilities
- [ ] validate External Knowledge → Qdrant
- [ ] validate query embedding compatibility with Qwen3-Embedding-4B / 2560 dimensions
- [ ] validate Knowledge Base behavior
- [ ] validate Folder/workspace + System Prompt + Knowledge behavior
- [ ] validate Filter / `file_handler`
- [ ] validate OpenAPI tool server integration
- [ ] validate MCP integration where useful
- [ ] select production upload/retrieval path
- [ ] prevent duplicate Open WebUI production vector indexing

#### C2 — Corporate document upload and document intelligence
- [ ] preserve Open WebUI upload UX
- [ ] route uploads into Document Ingestion
- [ ] register metadata/version before indexing
- [ ] preserve original files outside Qdrant
- [ ] validate DOCX/XLSX/PPTX/CSV end-to-end
- [ ] integrate PDF/OCR/Vision
- [ ] preserve page/section/table/slide provenance
- [ ] expose document inspection and analysis operations
- [ ] validate current/superseded version behavior

#### C3 — Corporate Knowledge and Workspace layer
- [ ] expose Corporate Knowledge through Knowledge Engine or validated external Qdrant integration
- [ ] map Open WebUI Knowledge to authoritative Corporate AI scopes
- [ ] enforce version/lifecycle/project/access filters
- [ ] preserve evidence claims and citations
- [ ] configure reusable Corporate AI models
- [ ] configure domain-specific Folders/workspaces
- [ ] configure system prompts and Skills
- [ ] expose controlled corporate tools
- [ ] validate focused retrieval vs full-context behavior
- [ ] validate agentic document retrieval for large document sets

#### C4 — Corporate Tools and artifact generation
- [ ] Knowledge Search tool
- [ ] Document inspection tool
- [ ] Document comparison tool
- [ ] whole-document analysis workflow
- [ ] Word generation
- [ ] Excel generation
- [ ] PowerPoint generation
- [ ] PDF generation
- [ ] preview-before-side-effect workflow
- [ ] artifact provenance / source traceability

#### C5 — Controlled Web Search
- [ ] decide SearXNG vs hosted provider
- [ ] deploy controlled search egress
- [ ] normalize web evidence
- [ ] implement bounded URL fetching
- [ ] preserve URL and retrieval timestamp provenance
- [ ] add domain/timeout/size/concurrency controls
- [ ] isolate web prompt injection
- [ ] keep LLM network access disabled
- [ ] expose explicit web-search mode
- [ ] implement internal-first/web-fallback mode
- [ ] implement internal-only/offline mode

#### C6 — Agent and reasoning workflows
- [ ] Agent Controller
- [ ] planning and multi-step execution
- [ ] internal-first/web-fallback policy
- [ ] cross-document reasoning
- [ ] cross-source evidence evaluation
- [ ] contradiction handling
- [ ] confirmation for high-impact actions
- [ ] artifact traceability
- [ ] bounded resource policy and controlled failure modes

#### C7 — DGX acceptance
- [ ] UI upload → Document Ingestion → PostgreSQL → Qdrant
- [ ] internal grounded query
- [ ] multi-document query
- [ ] whole-document analysis
- [ ] current/superseded version test
- [ ] explicit web query
- [ ] mixed internal + web query
- [ ] citation/provenance verification
- [ ] blocked-domain and prompt-injection tests
- [ ] timeout/resource exhaustion tests
- [ ] internal-only/offline mode
- [ ] Open WebUI Folder/Knowledge/Tools acceptance

## Phase 4 — Multimodal

Vision; PDF/image pipeline; structured extraction.

**Status: FOUNDATION VALIDATED / INTEGRATION IN PROGRESS**

Completed:
- PDF classifier/router/preprocessor pipeline prototypes.
- Qwen3.6 Vision API validation.
- Structured Vision JSON validation.
- TABLE, VISUAL and COMPLEX page handling.

Next:
- Integrate OCR/Vision into Document Ingestion Service.
- Connect the already validated PDF native extraction path to the multimodal flow where OCR/Vision is required.
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
- harden Paperless webhook acknowledgement/timeout behavior.
- backup/recovery validation.
- evaluation suite.
- observability.
- resource contention tests.
- security hardening.
- deployment reproducibility.
