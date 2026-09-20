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

## Current validation checkpoint

- Qwen3.6 production configuration validated: 262144 context, GPU utilization 0.65, KV FP8, tool calling enabled.
- Qwen3.6 vision request validated.
- Vision JSON Schema validated.
- Qwen3-Embedding-4B local API validated with 2560-dimensional vectors and semantic similarity test.
- Qdrant production collection `corporate_knowledge` validated.
- Knowledge Engine health, search, ingest and end-to-end RAG query validated.
- Positive grounded RAG query validated.
- Negative query correctly returns the controlled no-answer response.
- Retrieval of a deliberate 60 EUR / 40 EUR conflict validated.
- Candidate numeric conflict detector validated as a prototype, but deliberately not integrated into production query flow yet.

## 19. Document Metadata and Version Foundation

The Document Ingestion module uses PostgreSQL as the authoritative metadata/version registry. Qdrant receives the retrieval-relevant metadata as payload and supports document/version/lifecycle filtering. A new successful version becomes CURRENT only after indexing; the previous CURRENT version becomes SUPERSEDED. Failed or incomplete ingestions are not promoted to CURRENT.
