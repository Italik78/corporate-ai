# CURRENT STATUS

**Checkpoint:** 2026-09-19

## Project

Corporate AI on NVIDIA DGX Spark GB10. GitHub repository is the source of truth.

## Runtime

- DGX Spark GB10, 128 GB unified memory, 4 TB NVMe.
- Ubuntu 24.04.x LTS, aarch64.
- NVIDIA Driver 580.178.04, CUDA 13.0.
- Docker 29.6.2, NVIDIA Container Toolkit 1.20.0.
- Internal Docker network: `ai-net`.
- Primary LLM: Qwen3.6-35B-A3B-NVFP4.
- Qwen3.6: context 262144, GPU utilization 0.65, KV FP8, MTP 3, tool calling enabled, thinking disabled for standard mode.
- Qwen3.6 Vision pipeline foundation is validated.

## Knowledge foundation

- Qwen3-Embedding-4B, 2560 dimensions, local embedding service.
- Qdrant `corporate_knowledge`, persistent production storage.
- Knowledge Engine provides:
  - `/health`
  - `/v1/search`
  - `/v1/ingest`
  - `/v1/query`
- End-to-end grounded RAG is validated.
- Insufficient evidence is returned as:
  `Няма достатъчно информация в предоставените документи.`
- Deliberate conflicting claims are retrieved together.

## Evidence Engine

Evidence Engine v0.1 is implemented as a separate module and integrated into Knowledge Engine `/v1/query`.

Supported statuses:

- `SUPPORTED`
- `CONFLICT`
- `INSUFFICIENT_EVIDENCE`

Validated scenarios:

1. SUPPORTED
   - Relevant evidence is retrieved.
   - LLM generates the answer.
   - Source IDs are preserved.

2. CONFLICT
   - Conflicting relevant numeric claims are detected.
   - The system does not silently select a winning source.
   - Relevant evidence sources are returned.
   - The LLM does not generate a final answer.

3. INSUFFICIENT_EVIDENCE
   - Evidence is insufficient.
   - A controlled no-answer response is returned.
   - Information is not fabricated.

Current limitation:

- The numeric conflict detector is a candidate detector, not a final semantic conflict resolver.
- `answerable=True` currently means that no relevant numeric conflict was detected. It does not prove complete semantic answerability.
- Final groundedness and answerability still include the LLM layer.

## Document intelligence

Universal target formats:

- PDF
- DOCX / DOC
- XLSX
- PPTX
- CSV
- TXT / Markdown
- Images

Validated foundation:

- PDF classifier.
- PDF router.
- Vision preprocessor.
- Qwen3.6 Vision adapter.
- Structured Vision JSON output.
- TABLE page handling.
- VISUAL page handling.
- COMPLEX page handling.

Next:

- Universal ingestion orchestration.
- Multimodal content normalization.
- Table and visual grounding.
- Integration with Knowledge Engine.

## Agent and tools

Architecture target:

```
Qwen3.6
   ↓
Agent Controller
   ↓
Knowledge / Files / Tools
   ↓
Tool Policy + Validation + Approval
   ↓
Document generation / actions
```

Office tools are intended for controlled Word/Excel/PowerPoint/PDF creation and reading. Write operations require human approval.

Open WebUI is the primary chat/UI layer. Corporate AI Console is separate and focuses on infrastructure/application topology, health, dependencies, resources, logs and operational status.

## Current phase

### PHASE 3: Evidence and Grounded Reasoning

Status: IN PROGRESS

Completed:

- Evidence Engine v0.1.
- SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE statuses.
- Source ID preservation.
- Conflict response without selecting a winning source.
- Integration into Knowledge Engine `/v1/query`.
- Live validation of all three main scenarios.

Next:

1. Expand Evidence Engine unit tests.
2. Finalize Evidence API contract.
3. Add claims and provenance model.
4. Add partial grounded answers for mixed questions.
5. Add conditional reranking / evidence fusion.
6. Improve semantic conflict detection.

## Current blockers

No blocker for the current development path.

The next work consists of engineering extensions to an already working foundation.

## Immediate next steps

1. Evidence Engine test and API contract expansion.
2. Universal document ingestion orchestration.
3. Multimodal and table grounding.
4. Retrieval quality improvements.
5. Agent Controller and Tool Policy.
6. Office Tool Gateway.
7. Open WebUI and Corporate AI Console integration.
8. Security hardening.
9. Production readiness.

## Project rules

- Status is changed to DONE / COMPLETE only after real technical validation.
- Documentation, plans and configuration alone do not count as implemented functionality.
- Old tasks are not marked DONE without verification against the current architecture.
- GitHub is the source of truth for project documentation.
