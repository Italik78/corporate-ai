# RISKS

- Kernel 7.0.0-1019-nvidia has a current NVIDIA forum report concerning NCCL/RoCE multi-node behavior. Validate against the actual workload before any kernel change.
- GPU/RAM contention between LLM, embeddings, vision and tools.
- RAG hallucination when evidence is insufficient.
- Document prompt injection from untrusted files.
- Tool misuse without policy/approval.
- Configuration drift between DGX and Git.
- Loss of persistent vector data without backup.
- Version drift from floating container image tags.