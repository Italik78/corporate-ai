# RAG

Previous working flow: query embedding → parallel Qdrant search across 12+ collections → exclude summary/very short chunks → hybrid rerank with Qwen3 reranker and keyword boost → conditional rerank → context builder with historical limit about 12k characters → Qwen3.6 grounding prompt → citations and structured sources.

V2 expands retrieval to vector + keyword + metadata + graph evidence followed by evidence fusion and grounded generation.