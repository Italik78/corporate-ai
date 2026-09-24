# DECISIONS

## 2026-09-18

1. Rebuild the Corporate AI architecture rather than blindly restarting the old stack.
2. Preserve existing working components, images, volumes and configurations.
3. Use NVIDIA-provided DGX Spark stack where it fits before writing custom infrastructure.
4. Keep NVIDIA DGX Dashboard for system operations.
5. Add a separate Corporate AI Console for application topology and service health.
6. Qwen3.6-35B-A3B-NVFP4 remains the initial primary LLM.
7. GitHub repository Italik78/corporate-ai is the project source of truth.
8. No destructive cleanup during migration until data/config inventory is complete.
9. Use Qwen3-Embedding-4B (2560 dimensions) as the primary local embedding model.
10. Use Qdrant as the production vector store on the internal ai-net network with persistent storage.
11. Treat Knowledge Engine as the boundary between retrieval/evidence and the LLM answer layer.
12. Do not let the LLM silently choose between conflicting sources. Evidence evaluation must explicitly distinguish SUPPORTED, CONFLICT and INSUFFICIENT_EVIDENCE.
13. Keep the current numeric conflict detector as a candidate detector only; do not use it as the final semantic conflict resolver.
14. Build Evidence Engine as a separate module before integrating conflict handling into /v1/query.
15. Keep Open WebUI as the primary user interaction layer; Corporate AI Console is for infrastructure/application topology and service status, not a second chat UI.

## 2026-09-22 — Platform architecture baseline

16. Corporate AI is a platform, not a single chat application.
17. Corporate AI Gateway is the controlled entry point for UI, API and automation clients.
18. AI Agent/Orchestrator is responsible for planning, context assembly, memory, skills, prompts, knowledge retrieval, Web Research, tools and long-running tasks.
19. Qwen3.6 remains the primary reasoning/generation engine; it is not the source of truth.
20. Corporate knowledge lives in a controlled Document Repository. Qdrant is an index, not canonical document storage.
21. Web Research is a controlled capability. Qwen3.6 has no unrestricted Internet access.
22. Internal Knowledge and Web Research share a common Evidence/Provenance model.
23. Memory is a separate capability with short-term conversation, long-term conversation, project memory, task state and optional user-preference memory.
24. Corporate documents are not conversational memory; they remain canonical Knowledge Repository content.
25. Long-running tasks are durable stateful jobs with checkpoints, events, evidence, artifacts, retries, cancellation and result retrieval.
26. Skills are versioned capability contracts; prompts are independently versioned artifacts in a Prompt Registry.
27. Production skill/prompt versions are immutable and auditable.
28. Context is assembled selectively. The system must not send entire conversation history, all project knowledge or whole documents to the LLM by default.
29. Phase 1 may temporarily reduce Qwen context from 256K to 128K to make room for the complete platform. The runtime change is subject to separate validation.
30. First objective is an end-to-end functional platform on one DGX Spark. Scale-out to multiple DGX/CPU/data servers follows measurement and acceptance.
31. Paperless-ngx is not part of the target architecture. Repository implementation remains an explicit abstraction; candidate repositories are evaluated separately.
32. No component is considered production-ready from documentation alone; end-to-end acceptance is required.

## 2026-09-24 — Document Ingestion implementation checkpoint

33. Universal file ingestion is implemented as a separate Document Ingestion Service between canonical document storage and downstream Knowledge Engine indexing.
34. Document metadata and version state are persisted in PostgreSQL; Qdrant remains an index and not canonical document storage.
35. Duplicate/version detection uses document content hash and must be deterministic and idempotent.
36. Duplicate lookup uses psycopg `dict_row` so database rows are consumed through named fields rather than positional assumptions.
37. Duplicate detection is accepted at unit-test level, but the complete Document Ingestion Service is not accepted until a real document completes indexing and lifecycle finalization successfully.
38. The `DocumentVersionResponse.tags` incident was traced to a stale pre-restart runtime, not to the current metadata/indexing contract. No response-schema workaround was introduced.
39. Real XLSX ingestion acceptance requires metadata registration, canonical source persistence, chunk indexing and lifecycle finalization to be verified together; a READY/CURRENT record plus successful Knowledge Engine retrieval is the acceptance evidence.

## Current validation checkpoint

- Qwen3.6 production configuration validated: 262144 context, GPU utilization 0.65, KV FP8, tool calling enabled.
- Qwen3.6 vision request validated.
- Vision JSON Schema validated.
- Qwen3-Embedding-4B local API validated with 2560-dimensional vectors and semantic similarity test.
- Qdrant production collection corporate_knowledge validated.
- Knowledge Engine health, search, ingest and end-to-end RAG query validated.
- Positive grounded RAG query validated.
- Negative query correctly returns the controlled no-answer response.
- Retrieval of a deliberate 60 EUR / 40 EUR conflict validated.
- Candidate numeric conflict detector validated as a prototype, but deliberately not integrated into production query flow yet.
- Document Ingestion duplicate lookup correction validated by targeted unit test.
- Document Ingestion application compilation, image rebuild and container startup validated.
- Real XLSX ingestion acceptance completed successfully after rebuilding/restarting the current Document Ingestion runtime: ingestion `6e220d34-abd9-46d0-99e5-befe4c97c4b0` reached `READY`, document version `v1` is `CURRENT`, canonical storage is populated, and Knowledge Engine retrieval returns indexed chunks.
