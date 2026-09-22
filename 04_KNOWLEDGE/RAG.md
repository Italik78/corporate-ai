# RAG

## Target flow

Question → query embedding → Qdrant retrieval → ACL/metadata filtering → conditional reranking → evidence fusion → context builder → Qwen3.6 → grounded response + citations.

## Retrieval sources

V2 may combine:
- vector evidence
- keyword evidence
- metadata constraints
- optional graph evidence
- document/version scope

## Conditional reranking

Qwen3-Reranker-0.6B runs on CPU to preserve unified memory/GPU capacity for the primary LLM and other AI workloads.

Reranking should be conditional:
- skip when retrieval confidence is sufficient
- rerank when ambiguity/competition requires it
- do not spend CPU latency only for coverage

## Evidence

Retrieved content becomes evidence with provenance.

Evidence states:
- SUPPORTED
- CONFLICT
- INSUFFICIENT_EVIDENCE

The answer layer must not silently choose between conflicting claims.

## Context

Context Builder selects only relevant chunks and metadata. Large documents are not inserted wholesale into the LLM context.

## Deletion/versioning

When a canonical document is deleted, deprecated or replaced, its searchable/indexed representations must follow the repository lifecycle so stale knowledge is not returned.

## Web Research relationship

Web Research uses the same evidence/provenance principles but has a separate controlled acquisition path for external sources.

## Current validated foundation

- Qwen3-Embedding-4B
- Qdrant corporate_knowledge
- Knowledge Engine search/ingest/query
- grounded positive query
- controlled insufficient-evidence response
- deliberate conflicting claims retrieved together
