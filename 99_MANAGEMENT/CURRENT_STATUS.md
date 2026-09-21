# CURRENT STATUS

**Checkpoint:** 2026-09-21

## Project

Corporate AI on NVIDIA DGX Spark GB10. GitHub repository is the source of truth.

## Runtime

- DGX Spark GB10, 128 GB unified memory, 4 TB NVMe.
- Ubuntu 24.04.x LTS, aarch64.
- NVIDIA Driver 580.x, CUDA 13.x.
- Docker + NVIDIA Container Toolkit.
- Internal Docker network: `ai-net`.
- Primary LLM: Qwen3.6-35B-A3B-NVFP4.
- Qwen3.6: context 262144, GPU utilization 0.65, KV FP8, MTP 3, tool calling enabled, thinking disabled for standard mode.
- Qwen3.6 Vision pipeline foundation is validated.

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

Architecture decision:
- Universal file ingestion is a separate **Document Ingestion Service**.
- Knowledge Engine remains a normalized chunk → embedding → Qdrant/RAG service.
- MinIO is the planned production Object Storage on **AI-DATA-01**, not on DGX Spark.
- Original documents remain in Object Storage; Qdrant is an index, not the source of truth.

New architecture documents:
- `04_KNOWLEDGE/DOCUMENT_INGESTION_SERVICE.md`
- `04_KNOWLEDGE/DOCUMENT_AND_KNOWLEDGE_ARCHITECTURE.md`

## Infrastructure

Planned Data Server:
- Role: PostgreSQL, Vector DB, Object Storage.
- Target: 16 CPU cores, 64 GB RAM, 2 TB NVMe.
- 10 GbE and RAID are architectural requirements.

Current verified DGX deployment does not contain MinIO.
No production AI-DATA-01 runtime has been verified yet.

## Current phase

### PHASE 3: Knowledge / Grounded Reasoning

Status: IN PROGRESS

Completed:
- Embedding and Qdrant foundation.
- Knowledge Engine search/ingest/query.
- SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE handling.
- Grounded RAG validation.
- Knowledge Engine 0.3.1 stabilization.
- Document Ingestion Service skeleton and metadata/version registry.
- TXT/Markdown/DOCX/XLSX/PPTX/CSV extraction foundation.
- Deterministic chunking and SHA-256/version foundation.
- Knowledge Engine `/v1/ingest` integration.
- End-to-end ingestion and Qdrant indexing validation.
- PDF native-text extraction with page/block provenance.
- PDF ingestion → Knowledge Engine → Qdrant E2E validation.
- Paperless-ngx integration endpoint and webhook authentication foundation.
- Paperless webhook workflow investigation; exact Paperless webhook action path and placeholder syntax verified.

Current work:
- Paperless-ngx → Document Ingestion webhook E2E is not yet accepted.
- Paperless workflow currently needs final webhook payload configuration/debugging.
- Paperless DOCX/XLSX MIME acceptance still needs configuration if those formats are to enter through Paperless.
- PDF Vision/OCR integration remains after native PDF extraction.

Immediate next steps:
1. Fix and validate Paperless webhook E2E with a TXT test.
2. Verify `paperless:<document_id>` version registration and Qdrant indexing.
3. Configure/validate Paperless support for DOCX/XLSX if required.
4. Run several real documents through Paperless → Document Ingestion → Knowledge Engine.
5. Integrate PDF/OCR/Vision into Document Ingestion Service.
6. Update project documentation/status after acceptance.

## Runtime cleanup note

Older Knowledge Engine test containers remain on the DGX during validation. They are not removed until the active 0.3.1 path is fully accepted.

## Project rules

- Status changes to DONE/COMPLETE only after real technical validation.
- Documentation, plans and configuration alone do not count as implemented functionality.
- Original documents are not stored in Qdrant.
- Document content is untrusted input and never overrides system/tool policies.
- GitHub is the source of truth for project documentation.
