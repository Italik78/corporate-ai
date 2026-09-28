# PROJECT MASTER

## Цел
Изграждане на локален Corporate AI върху NVIDIA DGX Spark GB10. Основните модели и AI услуги работят локално. Документите са недоверени входове. Knowledge/RAG отговорите са grounded с източници и явна неопределеност при липса на доказателства.

## База
- NVIDIA DGX Spark GB10
- 128 GB unified memory
- 4 TB NVMe
- Ubuntu 24.04.5 LTS
- NVIDIA Driver 580.178.04
- CUDA 13.0
- Docker 29.6.2
- NVIDIA Container Toolkit 1.20.0
- Docker network: ai-net

## Основен LLM
Qwen3.6-35B-A3B-NVFP4 чрез vLLM.
- served name: qwen36
- port: 8000
- context: 262144
- GPU utilization: 0.65
- KV cache FP8
- reasoning parser: qwen3
- tool choice: enabled
- tool-call-parser: qwen3_coder
- thinking: disabled за стандартния режим
- speculative MTP: 3

## Основни подсистеми

Document & Knowledge Architecture v1 is the architectural baseline for large-document handling, normalized document structure, provenance, versioning, scoped retrieval and Agent document analysis. Original files are separate from the vector index.
LLM, embeddings, Qdrant, reranker, universal document ingestion, PDF/Vision, RAG, knowledge graph, agent/tool gateway, Office tools, Open WebUI, Caddy, Corporate AI Console, monitoring, backup/recovery и evaluation.

## Принцип
Всеки service има ясна роля, версия, health check, persistent storage при нужда, configuration, backup/recovery, dependencies, resource limits и logging. Не се правят destructive промени без предварителна проверка.

## Source of truth
GitHub repository Italik78/corporate-ai е source of truth за архитектурата, конфигурацията, кода и документацията.


## Current implementation milestone — Universal Document Ingestion — 2026-09-28

Document Ingestion Service 0.3.0 is the validated authoritative document entry point for the implemented ingestion paths. The DGX runtime now validates Nextcloud changed-file detection and versioning: the same source_reference resolves the same logical document_id, changed content creates the next version, and lifecycle transitions are persisted as SUPERSEDED → CURRENT. Canonical storage is version-specific and provenance is retained.

Pending: persistent Nextcloud poller state across container restart and Open WebUI upload integration.
