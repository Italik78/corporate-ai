# ROADMAP

## Phase 1 — Baseline

Verify DGX; inventory containers, images, volumes, networks and configs; preserve existing data.

**Status: COMPLETE**

## Phase 2 — Runtime

Declarative service definitions; Qwen3.6; health checks; resource policies.

**Status: COMPLETE**

## Phase 3 — Knowledge and Evidence

Embedding; Qdrant; Knowledge Engine; RAG; evidence evaluation; universal ingestion.

**Status: IN PROGRESS**

Completed:
- Qwen3-Embedding-4B production configuration and API validation.
- Qdrant corporate_knowledge collection and persistence validation.
- Knowledge Engine search/ingest/query.
- grounded positive query and insufficient-evidence negative query.
- conflict retrieval.
- Evidence Engine with SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE.
- evidence claims with source IDs.
- normalized RAG response contract.
- Knowledge Engine 0.3.1 test runtime validation.
- initial universal ingestion foundation.

Next:
1. Finish document repository lifecycle integration.
2. Complete document ingestion for all target formats.
3. Complete provenance/version/delete propagation.
4. Conditional reranking/evidence fusion.
5. Improve semantic conflict detection.
6. Validate ACL filtering before context construction.
7. Evaluate knowledge graph where it provides measurable value.

## Phase 4 — Multimodal Document Intelligence

PDF/OCR/Vision; images; structured extraction; table/visual grounding.

**Status: FOUNDATION VALIDATED / INTEGRATION IN PROGRESS**

Completed:
- PDF classifier/router/preprocessor prototypes.
- Qwen3.6 Vision API validation.
- structured Vision JSON validation.
- TABLE, VISUAL and COMPLEX page handling.
- native PDF extraction with provenance.
- PDF → chunk → embedding → Qdrant E2E validation.

Next:
- integrate OCR/Vision into Document Ingestion.
- ground visual/table extraction.
- propagate confidence and uncertainty.

## Phase 5 — Platform Gateway and Agent

Gateway; Agent/Orchestrator; policy; memory; skills; prompts; Task Engine; Tool Gateway.

**Status: ARCHITECTURE BASELINE / IMPLEMENTATION IN PROGRESS**

Target:
- Corporate AI Gateway.
- Agent Controller.
- short/long-term conversation memory.
- Project Memory.
- long-running Task API and durable state.
- Skill Registry.
- Prompt Registry.
- Tool Policy and schema validation.
- Office Tool Gateway.
- human approval workflow.
- provenance and audit.

## Phase 6 — Controlled Web Research

Research planner; search/fetch; source classification; evidence; cross-checking; citations; prompt-injection isolation.

**Status: ARCHITECTURE BASELINE**

Target:
- controlled Internet access outside Qwen.
- primary-source preference.
- evidence/conflict handling.
- research report generation.
- long-running research tasks.

## Phase 7 — User and Operations Layer

Open WebUI/Pipe; streaming/status events; Corporate AI Console; monitoring.

**Status: FOUNDATION**

## Phase 8 — End-to-End Demonstration

Build representative workflows covering:
- internal knowledge question
- document analysis
- Web Research
- complex multi-step task
- document generation
- tool execution
- long-running task
- memory continuity
- conflict/insufficient-evidence cases

**Goal:** demonstrate the complete Corporate AI value proposition on one DGX Spark.

## Phase 9 — Evaluation and Production Readiness

Measure:
- factual correctness
- groundedness
- citation correctness
- retrieval/reranking
- Web Research quality
- memory correctness/isolation
- tool success
- task reliability
- latency
- concurrency
- CPU/RAM/GPU utilization
- ingestion throughput
- failure/recovery

**Status: NOT COMPLETE**

## Phase 10 — Scale-out

After measurable acceptance:
- second DGX Spark
- distributed LLM workers
- CPU worker pools
- dedicated database/object storage
- gateway/application nodes
- workload scheduling
- multi-node networking

Context size and concurrency are then tuned from measurements. A second DGX does not automatically increase the context window of one model instance.
