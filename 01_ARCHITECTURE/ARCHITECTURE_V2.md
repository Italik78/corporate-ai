# ARCHITECTURE V2

## Top-level

```
User / API / Automation
        ↓
Corporate AI Gateway
        ↓
AI Agent / Orchestrator
        ↓
┌────────────┬──────────────┬────────────┬──────────────┐
│ Knowledge  │ Web Research │ Tools      │ Document     │
│ + Evidence │ + Evidence   │ Gateway    │ + Vision     │
└────────────┴──────────────┴────────────┴──────────────┘
        ↓
Evidence / Provenance
        ↓
Qwen3.6
        ↓
Validation / citations / response
```

## Gateway

Auth, identity, ACL, session, policy, audit, request validation, task submission and rate/concurrency controls.

## Agent / Orchestrator

Planning, intent classification, context assembly, memory retrieval/write decisions, skill selection, prompt selection, retrieval, Web Research, tools, task checkpoints and final validation.

## Memory

Separate scoped stores for short-term conversation, long-term conversation, project memory, long-running task state and optional user preferences.

Corporate documents remain canonical Knowledge Repository content.

## Skills and prompts

Skills are versioned capability contracts. Prompts are versioned artifacts referenced by skills/tasks. Production versions are immutable.

## Knowledge

Repository → ingestion → normalized structure → embeddings → Qdrant → retrieval → conditional reranking → evidence fusion → context builder → Qwen3.6.

## Web Research

Agent → Web Research Service → search/fetch/extraction/sanitization/provenance → Web Evidence → Evidence Engine → Qwen3.6.

Qwen3.6 has no unrestricted Internet access.

## Tools

Agent → Tool Gateway → policy/ACL/schema/approval → tool execution → validated result → provenance/audit.

## Document intelligence

Input → security intake → classifier/router → extraction/OCR/Vision → normalized structure → metadata/versioning → chunking → Knowledge Engine.

## Long-running tasks

Gateway/Agent → Task Engine → durable plan/state/checkpoints/events → workers → evidence/artifacts → result.

## Evidence

Common model for internal and Web evidence:
- SUPPORTED
- CONFLICT
- INSUFFICIENT_EVIDENCE

The LLM does not silently resolve conflicts.

## Operational layer

NVIDIA DGX Dashboard handles system-level operations. Corporate AI Console handles application topology, health, dependencies, logs and resource state.

## Deployment

Phase 1: one DGX Spark with explicit resource budgets.

Future: distribute LLM workers, CPU services, data services and task workers across multiple servers while preserving API contracts.
