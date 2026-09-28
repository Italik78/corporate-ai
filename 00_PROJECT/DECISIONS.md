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

## 2026-09-28 — Universal Document Ingestion implementation foundation

42. Document Ingestion exposes `/v1/documents/ingest` as the primary multipart document entry point and `/v1/documents/process` for callers that require the normalized document response. Both route through the same ingestion pipeline and Repository boundary.
43. Persistent ingestion jobs in PostgreSQL are part of the document intake contract. Job state carries ingestion ID, document ID, version, processing status, lifecycle status and machine-readable failure information.
44. `source_reference` is a first-class document metadata field. It is persisted with document versions and propagated through upload, process, Paperless and duplicate reconstruction paths. Paperless uses the source namespace `paperless:{document_id}`.
45. Duplicate processing reconstructs the normalized document from authoritative indexed chunks instead of re-indexing the same content. Metadata and provenance are retained for the reconstructed document.
46. `source_system` and `source_reference` are distinct concepts: `source_system` identifies the producer/integration, while `source_reference` identifies the producer-side document identity or reference.
47. The current unit acceptance baseline for Document Ingestion is 24 passed, 0 failed. This validates the implementation foundation; Task 2 remains open until current changes receive real DGX runtime acceptance and the Open WebUI upload path is validated.


## 2026-09-28 — Nextcloud poller E2E versioning validation

48. Nextcloud polling is validated end-to-end against Document Ingestion: a changed file at the same source reference reuses the same logical document_id and creates the next document version.
49. The validated Nextcloud flow uses ETag change detection, downloads the changed file, submits it through /v1/documents/ingest, and preserves source_system="nextcloud" plus the source path as source_reference.
50. Version lifecycle transitions are validated on the DGX runtime: the previous version becomes SUPERSEDED, the new version becomes CURRENT, and supersedes / superseded_by relationships are persisted.
51. Persistent Nextcloud poller state across container restart remains a separate hardening task; the current state file is ephemeral and is not yet accepted as production-durable state.
