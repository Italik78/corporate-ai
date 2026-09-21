# CURRENT STATUS

**Checkpoint:** 2026-09-21

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
- Open WebUI architecture and Web Search baseline.
- Open WebUI confirmed on `ai-net`.

## Immediate execution order

1. **C1.1 — Inspect installed Open WebUI capabilities/version.**
2. **C1.2 — Validate Corporate Knowledge retrieval path without mismatched embeddings.**
3. **C1.3 — Validate Open WebUI Knowledge / Folder / System Prompt behavior.**
4. **C1.4 — Validate Filter/file_handler and OpenAPI/MCP extension points.**
5. **C2.1 — Implement controlled Open WebUI upload → Document Ingestion path.**
6. **C2.2 — Validate XLSX/DOCX/PPTX/CSV through the UI.**
7. **C2.3 — Integrate PDF/OCR/Vision.**
8. **C3 — Build authoritative Corporate Knowledge workspace integration.**
9. **C4 — Add document analysis and artifact tools.**
10. **C5 — Add controlled Web Search.**
11. **C6 — Integrate Agent workflows.**
12. **C7 — Execute complete DGX acceptance suite.**

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
