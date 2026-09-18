# RERANKER

Qwen3-Reranker-0.6B on CPU was previously served on port 8002.

Target: conditional rerank; skip when retrieval confidence is sufficient; rerank when ambiguity is high; do not increase CPU latency merely to maximize reranking coverage.