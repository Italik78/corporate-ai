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
- separate Document Ingestion Service foundation with PostgreSQL metadata/version persistence.
- content-hash duplicate/version detection foundation.
- duplicate lookup correction using psycopg `dict_row`.
- duplicate-specific unit test validation: `1 passed, 23 deselected`.
- Document Ingestion application compilation validation.
- Document Ingestion image rebuild and container startup validation.
- real XLSX processing reaches version/indexing and creates ingestion/document version records.
- real XLSX end-to-end acceptance completed: ingestion `6e220d34-abd9-46d0-99e5-befe4c97c4b0` is `READY`, document version `v1` is `CURRENT`, canonical storage is populated, and Knowledge Engine search returns indexed chunks from the document.
- the earlier `DocumentVersionResponse.tags` error was confirmed as belonging to a pre-restart runtime record; no schema workaround was introduced.
- stable Nextcloud `source_reference` is passed into Document Ingestion for current incoming files.
- Knowledge Engine RAG JSON truncation was resolved by increasing the RAG LLM `max_tokens` limit from 1024 to 8192.
- Gateway grounded answers were validated with human-readable citations and structured source provenance.
- lifecycle filtering by `CURRENT` was validated against real document versions.
- legacy document identity cleanup was validated: the old `proekt.docx` record and its 20 Qdrant chunks were moved from `CURRENT` to `ARCHIVED`, while the canonical source was preserved.
- final accounting-project RAG validation with `lifecycle_status=CURRENT` returned only the current `проект.docx` v2 source and produced `grounded=True`, `answer_status=FULL`.
- Nextcloud poller → Document Ingestion → MetaVox end-to-end path validated with a real PDF without warnings: `уведомително писмо ДБТ _signed.pdf` reached `READY`, 1 page, 1 chunk, 1 indexed chunk and `warnings=[]`; MetaVox was updated to `READY FOR RAG`, `rag_ready=1`.

Current status:
- Universal file ingestion foundation is accepted for the validated XLSX path.
- Nextcloud production-style polling path is validated for representative PDF, DOCX, XLS and PPTX inputs, including a clean no-warning PDF run.
- Current document-questioning/RAG path is accepted for further representative-document testing.
- Current-source filtering is verified after cleanup of the known legacy document identity.
- Repository archive/delete/restore semantics remain a Phase 2 gap; the legacy cleanup was a one-off controlled migration, not a new operational API.

Next:
1. Validate document analysis with additional representative documents and questions.
2. Validate analytical/reasoning questions while enforcing groundedness and provenance.
3. Complete repository lifecycle integration and Phase 2 archive/delete/restore semantics.
4. Complete provenance/version/delete propagation.
5. Integrate PDF/OCR/Vision into Document Ingestion.
6. Conditional reranking/evidence fusion.
7. Improve semantic conflict detection.
8. Validate ACL filtering before context construction.
9. Evaluate knowledge graph where it provides measurable value.

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

**Status: IMPLEMENTATION READY / NOT STARTED**

Architecture and implementation specification:
- `06_WEB_RESEARCH/WEBSEARCH_AGENT_SPEC.md`

Principles:
- Qwen3.6 has no unrestricted Internet access.
- Web access is provided only through a controlled WebSearch capability.
- Initial search provider is self-hosted SearXNG with explicitly configured engines.
- Search and URL fetching are policy-controlled operations.
- Web content is untrusted data and cannot modify system policy, tool permissions or ACL.
- SSRF protection and internal-network blocking are mandatory.
- Web evidence uses source IDs, URLs, hashes, timestamps, source metadata and citation IDs.
- Conflicting sources produce explicit conflict evidence rather than silent source selection.
- Research is bounded by search, fetch, iteration, size, timeout and concurrency limits.
- Initial validation is performed entirely through the DGX Spark runtime and SSH before Open WebUI integration.

Implementation sequence:
1. WEBSEARCH-001 — repository/runtime/network inspection.
2. WEBSEARCH-002 — API contracts and data models.
3. WEBSEARCH-003 — pinned SearXNG service and explicit engine configuration.
4. WEBSEARCH-004 — WebSearch service with `/health` and `/v1/search`.
5. WEBSEARCH-005 — controlled `/v1/fetch` with SSRF and resource limits.
6. WEBSEARCH-006 — evidence normalization and provenance.
7. WEBSEARCH-007 — bounded `/v1/research` workflow.
8. WEBSEARCH-008 — evidence conflict handling.
9. WEBSEARCH-009 — prompt-injection isolation and adversarial tests.
10. WEBSEARCH-010 — explicit-web, internal-only and internal-first → web-fallback modes.
11. WEBSEARCH-011 — complete SSH-based DGX E2E acceptance.
12. WEBSEARCH-012 — Agent/Orchestrator integration.
13. WEBSEARCH-013 — documentation, measurements and release checkpoint.

Acceptance target:
- basic Bulgarian and English search
- freshness constraints
- domain allowlists
- multi-source research
- deduplication
- unavailable sources
- conflicts
- SSRF/private-network blocking
- size/time/concurrency budgets
- prompt-injection isolation
- citation/provenance correctness
- all three operating modes
- complete DGX Spark E2E validation

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
