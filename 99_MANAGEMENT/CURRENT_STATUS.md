# CURRENT STATUS

**Checkpoint:** 2026-09-30

## Project

Corporate AI on NVIDIA DGX Spark GB10. GitHub repository is the source of truth.

### Current product target

The project target is a **Corporate Information System** built on Open WebUI + Corporate AI services.

Open WebUI is the primary user-facing workspace. Corporate AI remains authoritative for document ingestion, metadata/versioning, knowledge retrieval, evidence, security, tools, agents and provenance.

The intended system must understand shared documents as structured, versioned corporate information — not merely as isolated text chunks.

## Runtime

- DGX Spark GB10, 128 GB unified memory, 4 TB NVMe.
- Ubuntu 24.04.x LTS, aarch64.
- NVIDIA Driver 580.x, CUDA 13.x.
- Docker + NVIDIA Container Toolkit.
- Internal Docker network: `ai-net`.
- Primary LLM: Qwen3.6-35B-A3B-NVFP4.
- Qwen3.6: context 262144, GPU utilization 0.65, KV FP8, MTP 3, tool calling enabled, thinking disabled for standard mode.
- Qwen3.6 Vision pipeline foundation is validated.
- Open WebUI is connected to `ai-net` and currently has address `172.18.0.9`.

## Knowledge foundation

- Qwen3-Embedding-4B, 2560 dimensions, local embedding service.
- Qdrant collection: `corporate_knowledge`.
- Active Knowledge Engine test release: **0.3.1**.
- Active Knowledge Engine host API: `127.0.0.1:8093`.
- Knowledge Engine endpoints:
  - `/health`
  - `/v1/search`
  - `/v1/ingest`
  - `/v1/query`
- End-to-end grounded RAG is validated.
- Insufficient evidence returns a controlled no-answer response.
- Deliberate conflicting claims are retrieved together without silently selecting a winner.

## Document intelligence

Target formats:
- PDF
- DOCX / DOC
- XLSX
- PPTX
- CSV
- TXT / Markdown
- PNG / JPEG / TIFF

Validated foundation:
- PDF classifier.
- PDF router.
- Vision preprocessor.
- Qwen3.6 Vision adapter.
- Structured Vision JSON output.
- TABLE, VISUAL and COMPLEX page handling.

Architecture:
- Universal file ingestion is a separate **Document Ingestion Service**.
- Knowledge Engine remains a normalized chunk → embedding → Qdrant/RAG service.
- MinIO is the planned production Object Storage on **AI-DATA-01**, not on DGX Spark.
- Original documents remain in Object Storage; Qdrant is an index, not the source of truth.
- Large-document work is retrieval-first for ordinary questions and planned/bounded for whole-document analysis.

## Document Ingestion — current implementation checkpoint

The Document Ingestion Service now provides the production-oriented intake foundation required for Task 2.

Implemented:
- `POST /v1/documents/ingest` multipart upload entry point.
- `POST /v1/documents/process` entry point returning the normalized document.
- `POST /v1/integrations/paperless/webhook` controlled Paperless boundary with secret validation.
- Persistent `ingestion_jobs` status records in PostgreSQL.
- Bounded upload staging with filename/extension/size validation and SHA-256 hashing.
- Repository registration before indexing.
- Canonical source storage and canonical storage key persistence.
- Versioning, SHA-256 deduplication, lifecycle and supersession handling.
- Project and access-scope metadata.
- `source_reference` as a first-class metadata field across models, PostgreSQL version records, pipeline paths and duplicate reconstruction.
- Paperless source namespace `paperless:{document_id}`.
- Duplicate reconstruction from authoritative indexed chunks, preserving source metadata and provenance.
- Normalized extraction tests for TXT, Markdown, CSV, DOCX, XLSX, PPTX and native PDF text.

### Latest test checkpoint

`services/document-ingestion/tests/test_unit.py`

**24 passed, 0 failed, 6 warnings**

The warnings are non-fatal PyMuPDF deprecation warnings and pytest cache permission warnings.

### Source-reference change sequence validated by compilation

- `models.py` source-reference update → compile OK.
- `metadata.py` schema/source-reference updates → compile OK.
- `metadata.py` row mapping update → compile OK.
- `metadata.py` `register_version` source-reference persistence → compile OK.
- `pipeline.py` source-reference lookup and metadata propagation → compile OK.
- `main.py` `/v1/documents/ingest` and `/v1/documents/process` source-reference-related updates → compile OK.
- Paperless webhook source-reference integration → compile OK.
- Duplicate reconstruction fixture updated with `source_reference=None`; focused test passed and the full unit suite then passed.

### Current acceptance state

The **Nextcloud production document entry-point / poller E2E acceptance is COMPLETE** on the DGX runtime.

Validated with a genuinely new PDF, without duplicate reuse:
- Nextcloud WebDAV download succeeded.
- `POST /v1/documents/ingest` returned success and the pipeline reached `READY`.
- Version 1 was registered.
- PDF page count: 1.
- Chunks: 1.
- Indexed: 1.
- Warnings: `[]`.
- MetaVox write-back succeeded with `READY FOR RAG` and `rag_ready=1`.
- The following poll correctly skipped the unchanged file by ETag.

This closes the current Nextcloud → Document Ingestion → Knowledge Engine/Qdrant → MetaVox acceptance task.

Still pending for the broader Task 2 / production scope:
1. Open WebUI upload → Document Ingestion routing.
2. Validation that Open WebUI does not create independent `file-*` production collections.
3. Complete acceptance of scanned/complex PDF OCR/Vision through the production entry point.
4. Durable poller-state validation across container restart.

## Open WebUI discovery checkpoint

The Open WebUI container is already attached to `ai-net`:

- `open-webui`: 172.18.0.9
- `corporate-ai-qdrant`: 172.18.0.2
- `corporate-ai-embedding-test`: 172.18.0.4
- `corporate-ai-gateway-0.3.1`: 172.18.0.10
- `corporate-ai-document-ingestion`: 172.18.0.11
- `corporate-ai-qwen36`: 172.18.0.3

A real XLSX upload previously demonstrated the current integration boundary: Open WebUI processed the file with `sentence-transformers/all-MiniLM-L6-v2` and created an independent `file-*` collection instead of reaching Corporate Document Ingestion. This is an integration-path issue, not evidence that the Corporate XLSX extractor is broken.

The Open WebUI target is broader than upload integration. We will use its capabilities where they add value:

- Folders/workspaces;
- System Prompts;
- Knowledge;
- reusable Models;
- Skills;
- Tools;
- OpenAPI/MCP;
- Filters;
- Web Search.

These UI capabilities must remain backed by Corporate AI authoritative services where business/security/provenance matters.

## Current phase

### PHASE 3: Knowledge / Grounded Reasoning + Corporate Information System foundation

Status: IN PROGRESS

Completed:
- Embedding and Qdrant foundation.
- Knowledge Engine search/ingest/query.
- SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE handling.
- Grounded RAG validation.
- Knowledge Engine 0.3.1 stabilization.
- Document Ingestion Service architecture and metadata/version foundation.
- Document Ingestion Service 0.3.0 supports TXT, Markdown, CSV, DOCX, XLSX, PPTX and PDF.
- Paperless-ngx webhook ingestion validated with document ID, secret header and source provenance.
- PDF security intake false-positive for binary NUL bytes corrected; unit suite passed 17 tests.
- Office/tabular extraction implementation.
- Document Ingestion Service 0.3.0 runtime and unit validation.
- PDF native extraction with PyMuPDF 1.26.4, including page/block/bbox provenance.
- Paperless-ngx integration with Tika 3.3.1 and Gotenberg validated.
- Paperless → Document Ingestion → Knowledge Engine/Qdrant E2E validated for TXT, DOCX and XLSX.
- Persistent ingestion job/status foundation.
- Production-oriented `/v1/documents/ingest` and `/v1/documents/process` entry points.
- `source_reference` metadata foundation and persistence.
- Duplicate reconstruction from indexed chunks.
- Full document-ingestion unit baseline: 24 passed, 0 failed.
- Open WebUI architecture and Web Search baseline.
- Open WebUI confirmed on `ai-net`.

## Immediate execution order

1. **C2.1 / Task 2 acceptance — validate current ingestion changes on the DGX runtime.**
2. **C1.1 — Inspect installed Open WebUI capabilities/version.**
3. **C1.2 — Validate Corporate Knowledge retrieval path without mismatched embeddings.**
4. **C1.3 — Validate Open WebUI Knowledge / Folder / System Prompt behavior.**
5. **C1.4 — Validate Filter/file_handler and OpenAPI/MCP extension points.**
6. **C2.1 — Implement controlled Open WebUI upload → Document Ingestion path.**
7. **C2.2 — Validate XLSX/DOCX/PPTX/CSV through the UI.**
8. **C2.3 — Integrate PDF/OCR/Vision.**
9. **C3 — Build authoritative Corporate Knowledge workspace integration.**
10. **C4 — Add document analysis and artifact tools.**
11. **C5 — Add controlled Web Search.**
12. **C6 — Integrate Agent workflows.**
13. **C7 — Execute complete DGX acceptance suite.**

## Execution discipline

We will work **one command at a time**.

For each command:
1. I give the exact command.
2. User runs it on the DGX.
3. User returns the complete output.
4. I interpret it.
5. We decide the next command.
6. Only after validation do we update implementation status.

No guessed paths, container names, environment variables or Open WebUI settings when the runtime can tell us the truth.

## Project rules

- Status changes to DONE/COMPLETE only after real technical validation.
- Documentation, plans and configuration alone do not count as implemented functionality.
- Original documents are not stored in Qdrant.
- Document content is untrusted and never overrides system/tool policies.
- GitHub is the source of truth for project documentation.
- Open WebUI must not become a second authoritative corporate document store.
- Production retrieval against `corporate_knowledge` must use the Qwen3-Embedding-4B / 2560-dimensional embedding path or Knowledge Engine.
- LLM network access remains restricted; Web Search uses a controlled external boundary.

## Runtime cleanup note

Older Knowledge Engine test containers remain on the DGX during validation. They are not removed until the active 0.3.1 path is fully accepted.

## Document Metadata & Version Foundation — implemented

The Document Ingestion module includes persistent PostgreSQL metadata/version tracking, SHA-256 deduplication, automatic version increment when version 1 is re-submitted for an existing document, lifecycle states INGESTING/CURRENT/SUPERSEDED/ARCHIVED, document relationships, effective dates, project/access metadata, version metadata propagation to Qdrant, and version/lifecycle-aware Knowledge Engine filters.

Status: implementation complete; PDF/Office/Paperless runtime validation is complete for the validated paths; broader Phase B acceptance and Open WebUI integration remain pending.

## Paperless-ngx integration — validated

Paperless-ngx is connected to Document Ingestion through the dedicated webhook boundary. Tika 3.3.1 is used for text extraction and Gotenberg for Office-to-PDF conversion. Real documents were validated through Paperless → Document Ingestion → normalized chunks → embeddings → Qdrant/Knowledge Engine.

Validated examples:
- TXT: Paperless document ID 8 → `paperless:8` → Knowledge Engine retrieval.
- DOCX: Paperless document ID 10 → successful conversion/webhook → `paperless:10` retrieval with text provenance.
- XLSX: Paperless document ID 11 → successful conversion/webhook → `paperless:11` retrieval with TABLE provenance.

Known non-blocking observation: one XLSX test produced a Paperless webhook timeout log after the Document Ingestion service had already processed the request successfully. The current Paperless webhook client uses a short 5-second timeout; asynchronous acknowledgement/timeout hardening remains a future improvement.


## Nextcloud poller — runtime acceptance — 2026-09-28

The Nextcloud lab/source integration is now validated for changed-file versioning on the DGX runtime.

Validated:
- ETag change detection for the same Nextcloud path.
- Unchanged file is skipped when the ETag is unchanged.
- Changed valid DOCX is downloaded and submitted to Document Ingestion.
- source_system="nextcloud" and source_reference="Corporate AI/Incoming/проект.docx" are persisted.
- The same logical document_id is retained after the content changes.
- Changed content creates version 2.
- Version 1 becomes SUPERSEDED and version 2 becomes CURRENT.
- supersedes / superseded_by relationships are persisted.
- Canonical storage is version-specific for each document version.

Acceptance result: Nextcloud changed-file → same document_id → new version → lifecycle transition is COMPLETE.

Still pending for the broader task:
- persistent poller state across container restart;
- Open WebUI upload → Document Ingestion routing;
- final production E2E acceptance for all required UI and multimodal paths.


## 2026-09-30 — DGX restart, Vision stabilization and Nextcloud UI checkpoint

After the DGX restart/update the active stack was revalidated. The critical services are healthy: Document Ingestion 0.3.0 on :8095, Knowledge Engine 0.3.1-test on :8093, Gateway 0.3.3 on :8096, Qwen3.6, Qdrant, PostgreSQL and Nextcloud poller. The local Qwen3-Embedding-4B service was restarted after reboot and Knowledge Engine/Gateway health returned to fully OK.

### Document Ingestion fixes validated

- .xls ingestion is implemented and validated end-to-end through Nextcloud poller → Document Ingestion → Qdrant → Knowledge Engine.
- Multipart upload staging was hardened by increasing the Document Ingestion /tmp tmpfs to 512 MB; the previous 64 MB limit caused large multipart failures. A real 1.5 MB PDF subsequently reached application-level EMPTY_DOCUMENT, proving the transport limit was removed.
- IngestResponse now exposes page_count; successful PDF ingestion returns page count together with chunk/index counts.
- PDF Vision calls now request structured JSON with response_format={"type":"json_object"} and max_tokens=4096. A direct 87-page scanned-PDF Vision validation returned 87/87 successful pages with no PDF_VISION_INVALID_JSON failures. This closes the previously observed nondeterministic Vision JSON parsing defect at component-test level.
- The failed duplicate of A202401001-000-00_ Двустранно_подписан_договор (2).pdf was archived; the later E2E test copy changes only PDF metadata so its SHA-256 differs and deduplication cannot bypass Vision.

### Nextcloud MetaVox display checkpoint

Nextcloud MetaVox now exposes the Corporate AI processing state directly in the Corporate AI/Incoming file list. The six fields are visible as columns: corporate_ai_status, corporate_ai_version, corporate_ai_pages, corporate_ai_chunks, corporate_ai_indexed, and corporate_ai_rag_ready.

The test file A202600245-000-00_ Двустранно_подписан_договор.pdf (file ID 12914) displays READY FOR RAG, version 1, 92 pages, 348 chunks, 348 indexed and RAG ready. The other validated Incoming files were backfilled with their accepted ingestion metadata. MetaVox is the display layer; Corporate AI remains authoritative.

### Current pending validation — do not mark complete yet

A real 87-page scanned PDF E2E request is currently being executed through POST /v1/documents/process using the metadata-modified test file inside the Document Ingestion container, without an explicit document_id or version. The purpose is to validate the full real path after the Vision JSON-mode fix: upload → security → PDF routing → 87-page Vision → normalization → chunking → Knowledge Engine/Qdrant → READY.

The current request is still pending a final HTTP response. A previous monitoring attempt queried the non-existent /v1/documents/status endpoint and correctly returned HTTP 404; the valid status route is /v1/documents/{ingestion_id}/status, but the ingestion ID is not yet known from the running terminal request. Do not treat the 404 as an ingestion failure and do not interrupt the active E2E request.

### Post-E2E next steps

After the 87-page E2E result is known, update this checkpoint with the actual ingestion/document IDs and persisted status. Then continue with representative-format acceptance and the remaining Open WebUI upload integration work. No additional Vision code changes are planned unless the E2E test exposes a new defect.


## 2026-09-30 — Nextcloud clean E2E acceptance

A new document, `уведомително писмо ДБТ _signed.pdf`, was processed through the real Nextcloud poller path with no duplicate reuse and no warnings.

Acceptance result:
- download: successful;
- ingestion: `READY`;
- document_id: `b4a8fd9c-1d4d-4199-8e3e-0e1df252c80a`;
- version: 1;
- pages: 1;
- chunks: 1;
- indexed: 1;
- warnings: `[]`;
- MetaVox: `READY FOR RAG`;
- `rag_ready=1`;
- subsequent unchanged-file poll: correctly skipped by ETag.

The clean happy path is therefore accepted. A separate earlier 422 on `A202600303 Двустранно подписан.pdf` was successfully retried and is not part of this clean acceptance case; its successful retry also confirmed the error-detail logging path and duplicate reconstruction behavior.


## 2026-10-01 — Controlled Web Search / Gateway tool-loop checkpoint

### Completed and validated

- Controlled Web Search egress is deployed through SearXNG on the internal `ai-net`; the LLM itself has no unrestricted network access.
- Corporate AI Gateway exposes bounded `web_search` and `web_fetch` tools with explicit request validation and security limits.
- Qwen3.6 native tool calling was validated directly against the real Gateway tool schema.
- Gateway general chat now executes a bounded server-side tool loop, with a maximum of 4 tool iterations.
- The tool dispatcher validates tool arguments through the corresponding Pydantic request models before execution.
- `web_search` returns `retrieval_status=FOUND|NO_RESULTS` and preserves the raw search ranking as `ranking_score`.
- `web_fetch` returns `retrieval_status=FOUND|NO_RESULTS` and marks retrieved web content as `untrusted_content=true`.
- WEB retrieval semantics are explicitly separated from the internal RAG `evidence_status`; Evidence Engine semantics remain unchanged.
- Runtime smoke tests confirmed successful Web Search and Web Fetch execution.
- Gateway Web Search tests: 14 passed, 22 deselected; only the existing Starlette deprecation warning remains.

### Still open

- Web prompt-injection isolation.
- Explicit web-search mode.
- Internal-first / web-fallback mode.
- Internal-only / offline mode.
- Separate Web Evidence Evaluation layer above retrieval.
- Open WebUI upload → Document Ingestion production integration.

## 2026-10-02 — Authoritative current time context checkpoint

### Completed and validated

- Corporate AI Gateway now injects authoritative current date, local time, weekday, IANA timezone and UTC timestamp into every Qwen request.
- The default authoritative timezone is `Europe/Sofia` and can be configured through `CORPORATE_AI_TIMEZONE`.
- Time context is injected centrally at the Qwen transport layer, covering normal requests and the server-side tool loop.
- Duplicate time-context injection is prevented across repeated tool-loop calls.
- Runtime validation confirmed that the real Qwen model returns the current local date and time from the injected authoritative context.
- Gateway test suite: 39 passed; only the existing Starlette/AnyIO deprecation warning remains.
- Commit: `e279eee feat(gateway): provide authoritative current time to qwen`.

### Scope note

- This checkpoint covers Qwen calls routed through the Corporate AI Gateway. The separate Knowledge Engine LLM client remains a distinct integration point.
