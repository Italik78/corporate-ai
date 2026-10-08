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
16. Adopt `04_KNOWLEDGE/DOCUMENT_AND_KNOWLEDGE_ARCHITECTURE.md` as the baseline for large-document handling: original files remain outside Qdrant; ordinary questions use bounded retrieval; whole-document tasks use planned, bounded section-by-section analysis with provenance.
17. Do not use the Qwen3.6 262k context as the default destination for whole documents; large context is a capability margin for cases where broader context is justified.
18. Document versions, relationships, access scope and lifecycle must be represented in metadata so retrieval can select the applicable evidence.

## 2026-09-20

19. Adopt `04_KNOWLEDGE/OPEN_WEBUI_INTEGRATION_AND_WEB_SEARCH.md` as the baseline for Open WebUI integration and controlled Web Search.
20. Open WebUI remains the primary interaction layer, but it must not become a second authoritative document store, metadata registry or production vector index for Corporate AI knowledge.
21. The standard Open WebUI file RAG path must not be treated as the Corporate AI ingestion path because it can create independent `file-*` collections and use a different embedding model.
22. Before implementing a custom upload workaround, validate Open WebUI External Knowledge → Qdrant and the documented Filter `file_handler` extension point.
23. Corporate AI production retrieval must use Qwen3-Embedding-4B (2560 dimensions) or route through Knowledge Engine; mismatched Open WebUI embeddings must not query `corporate_knowledge`.
24. Web Search is an external evidence source, not an extension of internal corporate knowledge. Internal and web evidence must retain separate provenance.
25. The primary LLM must not have unrestricted Internet access. Web Search and URL fetching must execute through a controlled tool/service boundary with egress, domain, timeout, size, concurrency and prompt-injection controls.
26. Web content is untrusted data and cannot override system instructions, tool policy, access controls or authorization.
27. Support three web modes: explicit web search, internal-first/web-fallback when policy allows, and internal-only mode for confidential tasks.
28. Web Search should ultimately be exposed through the same Corporate AI Agent/Tool Policy and provenance model as other external tools, even when Open WebUI provides the user-facing search controls.
29. A self-hosted SearXNG deployment is the first candidate for controlled web search; a hosted search provider remains an alternative if quality/reliability requires it.
30. Documentation and plans are not implementation: Open WebUI integration and Web Search become complete only after DGX runtime validation.

## 2026-09-20 — Corporate Information System direction

31. The product target is a **Corporate Information System**. Open WebUI is the primary user workspace, not merely a chat frontend.
32. Use Open WebUI capabilities extensively where they improve the user experience: Folders/workspaces, System Prompts, Knowledge, reusable Models, Skills, Tools, Filters, OpenAPI, MCP and Web Search.
33. Corporate AI remains authoritative for document ingestion, metadata/versioning, access policy, embeddings, retrieval policy, evidence, provenance, Agent orchestration and business/security-critical tools.
34. Open WebUI Knowledge must not silently become a second authoritative knowledge store. Where it indexes or retrieves Corporate AI knowledge, it must either use the authoritative Corporate AI retrieval path or a validated compatible external index path.
35. Large-document understanding must support both retrieval-first questions and planned/agentic whole-document analysis. Full Context is a bounded capability, not the default strategy for arbitrary large documents.
36. Document understanding is a first-class capability: preserve document structure, tables, pages, sections, versions, relationships and provenance instead of reducing documents to anonymous text chunks.
37. The implementation process is command-by-command on the DGX with real runtime validation. Each milestone is marked complete only after technical acceptance.

## 2026-09-21 — Validated Document Ingestion / Paperless path

38. Document Ingestion Service 0.3.0 is the normalized ingestion boundary for TXT, Markdown, CSV, DOCX, XLSX, PPTX and PDF.
39. Paperless-ngx integrates through the dedicated webhook boundary; Tika 3.3.1 and Gotenberg are the validated extraction/conversion components.
40. Real Paperless → Document Ingestion → Qdrant/Knowledge Engine flows are validated for TXT, DOCX and XLSX, with provenance preserved.
41. A Paperless webhook timeout was observed after successful XLSX processing; this is tracked as a non-blocking timeout/acknowledgement hardening item.

## 2026-09-28 — Universal Document Ingestion / Production Entry Point

42. Document Ingestion Service 0.3.0 is the authoritative production entry point for document ingestion. The primary API is `/v1/documents/ingest`; `/v1/documents/process` is the explicit normalized-document return path.
43. Document ingestion must preserve `source_system` and optional `source_reference` from the entry point through PostgreSQL document-version metadata and reconstructed document responses. Source provenance must not be inferred later from filename or content.
44. Duplicate detection is performed using SHA-256 content hash together with the applicable access/project scope. A duplicate request must not create a new document version. When document content is requested through the process path, the existing normalized document is reconstructed from indexed chunks and persisted metadata.
45. The ingestion pipeline must register the document version before canonical source storage and Knowledge Engine indexing, then finalize the lifecycle state only after successful indexing.
46. Canonical original storage is part of the ingestion critical path. The original file is stored outside Qdrant and the resulting `canonical_storage_key` is persisted in document-version metadata.
47. Document Ingestion exposes a dedicated Paperless webhook boundary. Paperless-origin documents use `source_system="paperless"` and a stable `document_id` namespace derived from the Paperless document ID.
48. Metadata fields including tags, source reference, document dates, effective dates, project ID, access scope, classification and lifecycle state must survive the complete ingestion path and remain available to downstream retrieval and document reconstruction.
49. The Document Ingestion unit suite and real DGX smoke test are acceptance evidence for the implemented ingestion path. The current validated unit suite contains 38 passing tests. Open WebUI upload integration remains a separate pending acceptance item.
50. A successful ingestion is not considered complete merely because extraction succeeds. Technical acceptance requires metadata registration, canonical source persistence, Knowledge Engine indexing and final `CURRENT` lifecycle state.

## 2026-09-28 — Nextcloud poller E2E versioning validation

51. Nextcloud polling is validated end-to-end against Document Ingestion: a changed file at the same source reference reuses the same logical `document_id` and creates the next document version.
52. The validated Nextcloud flow uses ETag change detection, downloads the changed file, submits it through `/v1/documents/ingest`, and preserves `source_system="nextcloud"` plus the source path as `source_reference`.
53. Version lifecycle transitions are validated on the DGX runtime: the previous version becomes `SUPERSEDED`, the new version becomes `CURRENT`, and `supersedes` / `superseded_by` relationships are persisted.
54. Persistent Nextcloud poller state across container restart remains a separate hardening task; the current state file is ephemeral and is not yet accepted as production-durable state.

## 2026-09-30 — Vision, staging and UI decisions

55. PDF Vision structured-output calls use JSON response mode (`response_format={"type":"json_object"}`) with `max_tokens=4096`. This is a stability measure for scanned/complex PDF pages and was validated against an 87-page scanned PDF component test with 87/87 valid page results.
56. The successful PDF Vision component test is not by itself production E2E acceptance. The real `/v1/documents/process` path must be completed and its persisted READY/CURRENT state verified before marking the scanned-PDF E2E requirement complete.
57. Document Ingestion uses a 512 MB `/tmp` tmpfs because multipart upload staging can require more than the previous 64 MB boundary. This is a bounded runtime fix, not a change to the canonical storage architecture.
58. `page_count` is part of the successful `IngestResponse` contract for PDF processing so callers can populate operational UI metadata without changing the persistent document-version schema.
59. Nextcloud MetaVox is the current display-layer mechanism for showing Corporate AI processing state in the Nextcloud file list. It does not replace Corporate AI as the authoritative metadata, ingestion or retrieval system.
60. The current Corporate AI file-list display fields are status, version, pages, chunks, indexed count and RAG-ready state. These are operational presentation metadata and must be sourced from the authoritative ingestion result rather than independently computed by Nextcloud.
61. The monitoring route is `/v1/documents/{ingestion_id}/status`; `/v1/documents/status` does not exist and a 404 from that path is expected. The active E2E request must not be interrupted because of that monitoring mistake.

## 2026-10-03 — AI Orchestrator / grounded reasoning direction

62. Adopt `01_ARCHITECTURE/AI_ORCHESTRATOR.md` as the authoritative contract for the Corporate AI reasoning/orchestration layer.
63. The target product behavior is a grounded AI assistant that seeks the best verifiable answer rather than answering at any cost.
64. The Orchestrator sits between Corporate AI Gateway and specialized capabilities and coordinates task understanding, clarification, planning, Corporate RAG, Web Research, document analysis, controlled tools, evidence evaluation and verification.
65. Knowledge Engine remains the retrieval/evidence boundary. The Orchestrator must not duplicate it or become an alternative source of truth.
66. Corporate, Web and Tool/API evidence are separate provenance classes and must remain distinguishable through the complete workflow.
67. Retrieved documents, OCR output, Qdrant content, search results and web pages are untrusted data. None of them may authorize tools, alter policies or override system instructions.
68. The Orchestrator must ask clarification questions when missing context materially changes the answer and cannot be established through authorized sources or conversation context.
69. The Orchestrator may perform bounded iterative retrieval and task decomposition. It must operate under explicit tool, step, time and resource budgets.
70. Retrieval score alone is not an authority or truth criterion. Applicability must consider scope, version, authority, effective dates, conditions and semantic metric identity.
71. The first domain acceptance scenario for the general reasoning layer is conditional SLA reasoning. SLA values must not be hard-coded into the Orchestrator.
72. The final response may be a direct answer, conditional answer, partial answer, clarification request or controlled no-answer depending on the evidence state.
73. The system must preserve workflow traceability without exposing private model chain-of-thought.
74. Implementation will reuse the current Gateway, Knowledge Engine, Document Ingestion, Qdrant, PostgreSQL, controlled Web Search, Tool Policy and Qwen3.6 rather than replacing them with a separate platform.

## 2026-10-04 — Conversation & Context Management

75. Adopt `01_ARCHITECTURE/CONVERSATION_CONTEXT_MANAGEMENT.md` as the authoritative architecture for persistent conversation history, conversation state, contextual memory, milestones and dynamic LLM context construction.
76. Complete conversation history is persistent and must be separated from the bounded Working Context sent to the LLM.
77. Conversation State, Conversation Memory and Conversation Milestones are separate concepts and must not be collapsed into raw chat history or Corporate Knowledge.
78. PostgreSQL is the authoritative store for structured conversation history/state/memory/milestone records. Qdrant may provide derived semantic retrieval indexes but is not the authoritative memory store.
79. Corporate Knowledge evidence, Web evidence, Tool results and Conversation Memory are separate provenance classes and must remain distinguishable.
80. The Context Manager must build context dynamically from mandatory policy, conversation state, relevant history, memory, Corporate Knowledge evidence, Web evidence and tool results under an explicit token budget.
81. Qwen3.6 262144 context remains a capability ceiling. The default operating target is 24K–32K tokens for normal corporate chat, with adaptive expansion for complex tasks.
82. Large tool/web outputs must be persisted or summarized rather than appended indefinitely to conversation context.
83. Memory conflicts must not be silently resolved by recency, embedding similarity or model confidence alone.
84. Context construction and memory updates must preserve provenance and must not expose or persist private model chain-of-thought.


## 2026-10-04 — AI Brain / Intelligent Orchestration

85. The AI Orchestrator will evolve from predominantly deterministic task classification/planning into an **AI Brain + deterministic Control Plane** architecture.
86. The LLM Brain may understand, plan, select among authorized capabilities, evaluate evidence and request bounded re-planning, but it must never bypass security, authorization, tool policy, budgets or state validation.
87. Brain decisions must use a strict structured Decision Contract validated by Pydantic. Free-form model output must never be executed directly.
88. The deterministic Control Plane remains responsible for capability authorization, schema validation, dependency validation, budget enforcement, state transitions and execution.
89. Gateway capability authorization and Orchestrator capability selection are separate concerns. The client must not be able to elevate its own source/capability policy.
90. Standard Corporate AI operation must support server-side modes for INTERNAL_ONLY, INTERNAL_FIRST_WEB_FALLBACK, EXPLICIT_WEB and RESTRICTED_OFFLINE.
91. The existing deterministic classifier/planner remains a safe fallback until Brain-driven orchestration passes the acceptance matrix.
92. Brain re-planning is a first-class workflow capability after insufficient evidence, conflicts, failed verification or missing applicability.
93. Brain traceability must preserve decisions, selected capabilities, evidence references, budgets and outcomes without persisting or exposing private model chain-of-thought.
94. The implementation plan is documented in `01_ARCHITECTURE/AI_BRAIN_IMPLEMENTATION_PLAN.md`; the controlled implementation prompt is `99_MANAGEMENT/AI_BRAIN_NEW_CHAT_PROMPT.md`.
95. The first implementation milestone is Brain Decision Contract v1 + Control Plane validator. Production routing must not be switched to Brain-driven behavior before this contract is validated.


## 2026-10-08 — AI Brain implementation decisions

60. Keep `TaskType.CORPORATE_KNOWLEDGE` as the broad corporate task classification; structured tabular/document queries are a deterministic sub-classification, not a new top-level task type.

61. Deterministic structured-query detection must run before Qwen Brain planning when the request contains an unambiguous corporate structured-data intent. This prevents the LLM from unnecessarily choosing semantic RAG for a query that requires exact row/column filtering.

62. The deterministic structured-query parser may extract only information explicitly present in the user request. It must not invent sheet names, document IDs, column names, row positions or metadata.

63. Structured queries require an exact corporate document reference. Ambiguous source-file references must fail closed and request clarification rather than selecting an arbitrary document.

64. The structured-query capability remains behind the deterministic Control Plane and must preserve corporate provenance/evidence IDs.

65. The Brain may be bypassed for a deterministic structured query only when the parser produces a valid, schema-compatible and unambiguous capability request. Otherwise the request proceeds to Brain planning.

66. The deterministic planner remains the fallback when Brain execution is unavailable or invalid. Structured-query detection must be available to that fallback as well.

67. Parser correctness is a release gate. A parser that extracts only a suffix such as `(7.1).xls` from `DfQueryToExcel (7.1).xls` must not be integrated into production routing.
