# RISKS

- GPU/unified-memory contention between LLM, embeddings, vision, reranker and other services.
- Context size competing with memory required by the rest of the platform.
- RAG hallucination when evidence is insufficient.
- Web Research hallucination or weak-source synthesis.
- Prompt injection from untrusted documents and Web pages.
- Memory poisoning or persistence of incorrect information.
- Cross-project or cross-user memory leakage.
- Tool misuse without policy/approval.
- Skill/prompt version drift.
- Long-running task duplication, lost state or non-idempotent retries.
- ACL failure causing unauthorized information to enter LLM context.
- Configuration drift between DGX and Git.
- Loss of persistent vector/document data without backup.
- Version drift from floating container image tags.
- Resource exhaustion from concurrent research, ingestion or tasks.
- Scale-out/network issues when moving to multiple DGX nodes.
- Repository lifecycle mismatch causing stale/deleted documents to remain searchable.
- Source changes or disappearing Web pages affecting reproducibility.
- Document ingestion contract mismatch between metadata/version registration and downstream indexing.
- Duplicate/version detection errors causing duplicate documents or incorrect version state.
- Partial ingestion failures leaving metadata, canonical storage and index state inconsistent.

## Mitigations

- explicit resource budgets and monitoring
- selective context assembly
- scoped memory with provenance and deletion
- versioned skills/prompts
- durable task checkpoints and idempotency
- ACL enforcement before retrieval/context construction
- evidence validation and controlled no-answer states
- Web source provenance and cross-checking
- pinned versions
- backup/recovery tests
- benchmark suite before scale-out
- explicit Document Ingestion metadata/indexing contracts
- content-hash based duplicate/version detection with targeted regression tests
- real-document end-to-end acceptance before marking ingestion complete
- controlled failure states and persisted ingestion error codes
