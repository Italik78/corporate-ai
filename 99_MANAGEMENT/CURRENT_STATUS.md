# CURRENT STATUS

**Checkpoint:** 2026-09-18

## Project
Corporate AI on NVIDIA DGX Spark GB10. GitHub repository is the source of truth.

## Runtime
- DGX Spark GB10, 128 GB unified memory, 4 TB NVMe.
- Ubuntu 24.04.5 LTS, aarch64.
- NVIDIA Driver 580.178.04, CUDA 13.0.
- Docker 29.6.2, NVIDIA Container Toolkit 1.20.0.
- Internal Docker network: `ai-net`.
- Primary LLM: Qwen3.6-35B-A3B-NVFP4.
- Qwen3.6: context 262144, GPU utilization 0.65, KV FP8, MTP 3, tool calling enabled, thinking disabled for standard mode.

## Knowledge foundation
- Qwen3-Embedding-4B, 2560 dimensions, local vLLM pooling/embedding service.
- Qdrant `corporate_knowledge`, persistent production storage.
- Knowledge Engine provides:
  - `/health`
  - `/v1/search`
  - `/v1/ingest`
  - `/v1/query`
- End-to-end grounded RAG is validated.
- Insufficient evidence is returned as:
  `Няма достатъчно информация в предоставените документи.`

## Evidence checkpoint
A deliberate conflict test was created:
- Source 1: 60 EUR daily travel allowance.
- Source 2: 40 EUR daily travel allowance.
- Retrieval correctly returns both sources.
- A prototype numeric detector can flag the differing values, but it is intentionally not used as the final conflict resolver because simple numeric comparison produces false positives.
- Next component: standalone Evidence Engine v0.1.
- Required statuses:
  - `SUPPORTED`
  - `CONFLICT`
  - `INSUFFICIENT_EVIDENCE`
- Evidence Engine must preserve source IDs and must not silently select a winning source.

## Document intelligence
Universal target formats: PDF, DOCX, DOC, XLSX, PPTX, CSV, TXT and images.

Validated foundation:
- PDF classifier/router/preprocessor.
- Qwen3.6 vision.
- Structured vision JSON Schema.
- Table/visual/complex page handling prototypes.

## Agent/tool target
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

Office tools are intended for controlled Word/Excel/PowerPoint/PDF creation and reading. High-impact side effects require confirmation.

## Open WebUI
Open WebUI is the primary chat/UI layer. Built-in capabilities should be used where appropriate. Corporate AI Console is separate and focuses on infrastructure/application topology, health, dependencies, resources, logs and operational status.

## Immediate next steps
1. Implement Evidence Engine v0.1 as a separate module.
2. Unit-test SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE.
3. Integrate it into Knowledge Engine `/v1/query`.
4. Add partial grounded answers for mixed questions.
5. Continue toward universal document ingestion and Agent Controller.
