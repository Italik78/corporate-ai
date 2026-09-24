# CURRENT STATUS

**Checkpoint:** 2026-09-24

## Project

Corporate AI on NVIDIA DGX Spark GB10. GitHub repository is the source of truth.

The architecture baseline now covers Gateway, Agent/Orchestrator, Knowledge/Evidence, controlled Web Research, document/vision pipeline, memory, skills, prompt registry, long-running tasks, tools, provenance/audit and scale-out.

## Runtime

- DGX Spark GB10, 128 GB unified memory, 4 TB NVMe.
- Ubuntu 24.04.x LTS, aarch64.
- NVIDIA Driver 580.x, CUDA 13.x.
- Docker + NVIDIA Container Toolkit.
- Internal Docker network: ai-net.
- Primary LLM: Qwen3.6-35B-A3B-NVFP4.
- Qwen3.6 current runtime: context 262144, GPU utilization 0.65, KV FP8, MTP 3, tool calling enabled, thinking disabled for standard mode.
- Phase 1 architectural target allows temporary 128K context to free resources for the complete platform. Runtime change is not yet recorded as applied.
- Qwen3.6 Vision foundation is validated.

## Knowledge foundation

- Qwen3-Embedding-4B, 2560 dimensions, local embedding service.
- Qdrant collection: corporate_knowledge.
- Active Knowledge Engine test release: 0.3.1.
- Active Knowledge Engine host API: 127.0.0.1:8093.
- End-to-end grounded RAG is validated.
- Insufficient evidence returns a controlled no-answer response.
- Deliberate conflicting claims are retrieved together without silently selecting a winner.
- CPU reranker remains an intentional architecture component because unified memory/GPU capacity is constrained.

## Document intelligence

Target:
- PDF
- DOCX / DOC
- XLSX
- PPTX
- CSV
- TXT / Markdown
- PNG / JPEG / TIFF

Validated foundation:
- PDF classifier/router.
- Vision preprocessor.
- Qwen3.6 Vision adapter.
- structured Vision JSON.
- TABLE, VISUAL and COMPLEX page handling.
- native PDF extraction with provenance.
- PDF ingestion → Knowledge Engine → Qdrant E2E.

Architecture:
- Universal file ingestion is a separate Document Ingestion Service.
- Knowledge Engine receives normalized chunks.
- Original files remain in the repository/object storage; Qdrant is an index.
- Repository implementation is still an explicit architectural choice and must provide folder/version/ACL/delete semantics.

Paperless-ngx is removed from the target architecture and should not be reintroduced.

### Document Ingestion Service — current implementation checkpoint

The initial document ingestion service path is implemented and has been validated through unit and deployment checks.

Validated:
- PostgreSQL metadata persistence is active.
- Document version registration is present.
- Content-hash based duplicate/version detection is implemented.
- Duplicate lookup was corrected to use psycopg `dict_row` row mapping.
- Duplicate-specific unit test passes: `1 passed, 23 deselected`.
- Application compilation passes with `compileall`.
- Document Ingestion image rebuild succeeds.
- PostgreSQL health check and Document Ingestion container startup succeed.
- A real XLSX processing request reaches the version/indexing path and creates an ingestion record and document version.

Resolved validation incident:
- The earlier `DocumentVersionResponse.tags` error belongs to ingestion records created before the current container restart.
- Current source and runtime hashes for `pipeline.py` and `metadata.py` match.
- No `tags` field was added to `DocumentVersionResponse` as a workaround.

Successful real-document acceptance:
- ingestion_id: `6e220d34-abd9-46d0-99e5-befe4c97c4b0`
- document_id: `21f10869-8162-4c4f-88b7-1f16be934a83`
- version: `1`
- status: `READY`
- lifecycle_status: `CURRENT`
- `document_versions` contains the canonical storage key and `tags=[]`.
- Knowledge Engine search returns indexed chunks for the document, including `TABLE` / `table` chunks from `Traceability Matrix`.

The validated XLSX path is therefore accepted for the current Document Ingestion foundation. Broader repository lifecycle semantics and format coverage remain open.

## Platform components — architecture baseline

### Gateway / Agent
Defined:
- Corporate AI Gateway
- Agent/Orchestrator
- context assembly
- policy/ACL
- tool gateway
- long-running tasks

Implementation is not yet complete.

### Memory
Defined:
- short-term conversation memory
- long-term conversation memory
- Project Memory
- task state/memory
- optional user preference memory

Implementation is not yet complete.

### Skills / Prompts
Defined:
- Skill Registry
- Prompt Registry
- versioned contracts
- lifecycle
- tests
- audit

Implementation is not yet complete.

### Web Research
Defined:
- controlled search/fetch
- source classification
- provenance
- evidence/conflict handling
- citation validation
- prompt-injection isolation

Implementation is not yet complete.

## Current phase

### PHASE 3: Knowledge / Grounded Reasoning

Status: IN PROGRESS

Current technical work should continue on the accepted Knowledge/Document path, while the new platform services are implemented around it.

Immediate next steps:
1. Finish the document repository/integration decision and lifecycle contract.
2. Complete document ingestion provenance/version/delete propagation.
3. Integrate PDF/OCR/Vision into Document Ingestion.
5. Integrate PDF/OCR/Vision into Document Ingestion.
6. Complete semantic evidence/conflict handling.
7. Implement Gateway + Agent baseline.
8. Implement Memory baseline.
9. Implement Skill/Prompt registries.
10. Implement durable Task API/state.
11. Implement controlled Web Research.
12. Integrate Office/Tool Gateway and approval flow.
13. Build end-to-end benchmark scenarios.
14. Measure system before scale-out.

## Scale-out strategy

First prove the complete platform on one DGX Spark.

Then, based on measurements:
- add second DGX Spark
- distribute LLM/vision workers
- move CPU services to CPU nodes
- move data services to dedicated storage/database nodes
- add worker pools and scheduling

The logical architecture must remain stable.

## Project rules

- Status changes to DONE/COMPLETE only after real technical validation.
- Documentation, plans and configuration alone do not count as implemented functionality.
- Original documents are not stored in Qdrant.
- Document and Web content are untrusted input and never override system/tool policies.
- Memory does not automatically become corporate knowledge.
- LLM output is not evidence by itself.
- GitHub is the source of truth for project documentation.
