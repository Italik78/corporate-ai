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
