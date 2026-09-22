# CURRENT STATUS

**Checkpoint:** 2026-09-22

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
2. Complete document ingestion and provenance/version/delete propagation.
3. Integrate PDF/OCR/Vision into Document Ingestion.
4. Complete semantic evidence/conflict handling.
5. Implement Gateway + Agent baseline.
6. Implement Memory baseline.
7. Implement Skill/Prompt registries.
8. Implement durable Task API/state.
9. Implement controlled Web Research.
10. Integrate Office/Tool Gateway and approval flow.
11. Build end-to-end benchmark scenarios.
12. Measure system before scale-out.

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
