# Implementation Checkpoint — 2026-10-08

## Purpose

This checkpoint records the verified implementation state of the Corporate AI project as of 2026-10-08, before synchronizing the remaining local implementation work to GitHub.

GitHub repository: `Italik78/corporate-ai`  
Active development branch: `feature/corporate-ai-gateway-v0.1`

## Executive status

The project has moved beyond the basic RAG foundation. The validated platform now includes:

- authoritative Document Ingestion boundary;
- PostgreSQL document/version metadata;
- SHA-256 scoped duplicate detection;
- canonical original storage outside Qdrant;
- lifecycle/version handling;
- Knowledge Engine + Qdrant grounded retrieval;
- Paperless and Nextcloud ingestion paths;
- PDF native extraction and Vision component validation;
- controlled Web Search / Web Fetch through SearXNG and Gateway;
- Open WebUI native web tool calling;
- authoritative current-time context for Qwen;
- AI Brain + deterministic Control Plane architecture;
- structured corporate-document query capability for XLS/XLSX-style tabular data;
- bounded Brain decision contract and deterministic control-plane validation.

The last group is the current active implementation area. It is not yet equivalent to full production AI Brain acceptance.

## Verified implementation completed

### 1. Document and Knowledge foundation

Validated architecture and implementation include:

- Document Ingestion as the authoritative corporate document entry point.
- Source provenance through `source_system` and `source_reference`.
- Logical document identity and versioning.
- Lifecycle states including `INGESTING`, `CURRENT`, `SUPERSEDED`, `ARCHIVED`.
- SHA-256 duplicate detection within applicable scope.
- Canonical original storage outside Qdrant.
- Knowledge Engine indexing and grounded retrieval.
- Access/project/classification-aware metadata.
- Structured document metadata and provenance.

### 2. Document ingestion formats and integrations

Validated paths include:

- TXT;
- Markdown;
- CSV;
- DOCX;
- XLSX;
- PPTX;
- PDF;
- XLS/tabular extraction.

Paperless-ngx integration is validated through the dedicated webhook boundary.

Nextcloud polling is validated for:

- ETag change detection;
- unchanged-file skipping;
- same logical document ID for changed content;
- creation of a new document version;
- lifecycle transition `SUPERSEDED → CURRENT`;
- persisted version relationships;
- canonical version-specific storage.

Known remaining hardening item: durable Nextcloud poller state across container restart.

### 3. PDF / Vision

Validated:

- native PDF extraction with page/block/bounding-box provenance;
- 512 MB bounded temporary staging;
- structured JSON mode for PDF Vision;
- `max_tokens=4096`;
- 87/87 successful page-level Vision component results.

Important distinction:

The 87-page Vision component test is not by itself production E2E acceptance. The complete production path must still be accepted for scanned/complex PDF processing.

### 4. Controlled Web Research

Validated:

- SearXNG controlled search boundary;
- Gateway `web_search` and `web_fetch`;
- bounded server-side tool loop;
- Pydantic argument validation;
- explicit `FOUND|NO_RESULTS` retrieval status;
- web content marked as untrusted;
- separate web retrieval semantics from internal RAG evidence semantics;
- Open WebUI native function calling against the Gateway;
- real Web Search and Web Fetch runtime tests;
- Web Fetch response limit increased to 2 MiB after real-world validation.

Still open:

- web prompt-injection isolation;
- explicit web mode;
- internal-first/web-fallback policy;
- internal-only/offline mode;
- dedicated Web Evidence Evaluation layer.

### 5. Authoritative time context

Gateway now injects authoritative:

- local date;
- local time;
- weekday;
- IANA timezone;
- UTC timestamp

into Qwen requests, including the server-side tool loop.

Default timezone: `Europe/Sofia`.

### 6. Conversation & Context Management

Architecture has been accepted for:

- persistent conversation history;
- compact Conversation State;
- structured Conversation Memory;
- Conversation Milestones;
- dynamic Context Budget Manager;
- deterministic Context Builder;
- provenance-aware memory lifecycle;
- context-run telemetry;
- strict separation between conversation memory and corporate evidence.

Implementation is not yet complete.

### 7. AI Brain / Orchestrator implementation

The current Orchestrator has been extended with:

- `CapabilityType.STRUCTURED_QUERY`;
- strict Brain Decision v1 models;
- bounded Brain plan steps;
- deterministic Control Plane validation;
- capability authorization checks;
- dependency validation;
- source-policy validation;
- budget limits;
- structured-query input validation;
- dedicated structured query capability;
- Document Ingestion structured-query endpoint;
- ambiguity handling for duplicate/ambiguous source filenames;
- structured evidence IDs and corporate provenance;
- unit/integration coverage for the new structured-query path.

Current test evidence from the DGX development cycle:

- Document Ingestion structured-query tests: 8 passed;
- Document Ingestion suite excluding poller-state test: 58 passed;
- Orchestrator structured-query tests: 3 passed;
- Orchestrator full suite: 78 passed.

### 8. Real structured query validation

The authoritative file:

`DfQueryToExcel (7.1).xls`

was queried against sheet data with:

- `Край >= 05.10.2026`;
- `Край <= 31.01.2027`.

The validated structured query returned exactly 9 matching rows.

This proves that the deterministic backend capability can execute the requested tabular filtering and return corporate evidence.

## Current implementation gap

The important remaining defect is in Brain routing.

For a request such as:

> От файла DfQueryToExcel (7.1).xls намери договорите, при които колоната Край е между 05.10.2026 и 31.01.2027.

the real Qwen Brain currently selects `CORPORATE_RETRIEVAL` instead of `STRUCTURED_QUERY`.

The correct architecture is:

`classify_task → deterministic structured-query detection → valid structured query → STRUCTURED_QUERY`

Only when deterministic structured parsing is insufficient should the request proceed to Qwen Brain planning.

The new deterministic parser has been created locally, but its filename extraction was found to be incorrect during validation: it returned only `(7.1).xls` instead of the complete filename. This parser correction is therefore **not yet accepted** and must not be treated as production-ready.

## What is online in GitHub vs. local

The GitHub branch currently does **not yet contain all of the latest local AI Brain / structured-query implementation**.

In particular, the following latest local files/changes were not found on the online branch during the 2026-10-08 synchronization check:

- `services/ai-orchestrator/app/structured_query_parser.py`;
- latest local `models.py` structured-query changes;
- latest local `structured_query.py`;
- latest local `brain.py` changes;
- corresponding latest tests.

Therefore this checkpoint deliberately distinguishes:

- **implemented and validated locally**;
- **documented online**;
- **not yet synchronized to GitHub**.

No unverified code is claimed as online.

## Short remaining task list

1. Fix and test deterministic structured-query filename extraction.
2. Integrate deterministic structured-query detection into Brain routing.
3. Update affected Brain tests so deterministic structured queries bypass unnecessary LLM planning.
4. Run complete Orchestrator and Document Ingestion test suites.
5. Rebuild/restart only the affected Orchestrator service.
6. Run real DGX Brain/structured-query smoke tests.
7. Synchronize all accepted local code and tests to GitHub.
8. Update project status/roadmap after runtime acceptance.
9. Continue AI Brain phases: dynamic execution, evidence evaluation, re-planning, verification and policy modes.
10. Complete Conversation & Context Management implementation and runtime acceptance.
11. Complete Open WebUI upload → Document Ingestion production integration.
12. Complete web prompt-injection isolation and Web Evidence Evaluation.
13. Execute the final DGX acceptance matrix.

## Acceptance discipline

A feature is marked COMPLETE only after:

1. implementation;
2. focused tests;
3. affected-service build;
4. runtime smoke test;
5. persisted-state/log inspection where applicable;
6. Git synchronization;
7. documentation update.

GitHub remains the project source of truth.
