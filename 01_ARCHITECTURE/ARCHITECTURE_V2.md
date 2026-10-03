# ARCHITECTURE V2

Open WebUI → Corporate AI Gateway → AI Orchestrator → Qwen3.6 / Knowledge / Web / Tools / Vision.

## Orchestration path

```
Open WebUI
  ↓
Corporate AI Gateway
  ↓
AI Orchestrator
  ├── Conversation Context
  ├── Task Understanding
  ├── Clarification
  ├── Planning / Decomposition
  ├── Corporate Knowledge
  ├── Web Research
  ├── Document Analysis
  ├── Controlled Tools
  ├── Evidence / Truth Evaluation
  └── Verification
       ↓
Grounded Answer / Artifact
```

The Orchestrator is the coordination layer between the user-facing Gateway and specialized capabilities.

Knowledge Engine remains the retrieval/evidence boundary. Document Ingestion remains the authoritative document intake path. Tool Policy remains the authorization boundary.

## Knowledge path

query → task understanding → retrieval strategy → metadata/access/version filtering → vector/keyword retrieval → conditional reranking → evidence evaluation → applicability reasoning → context builder → Qwen3.6 → verified grounded response + sources.

## Agent path

Qwen3.6 ↔ AI Orchestrator → controlled tools.

The Orchestrator may plan and iterate within explicit budgets. Every tool has schema, policy, validation, logging and traceability.

## Source classes

- Corporate evidence
- Web evidence
- Tool/API evidence

These source classes retain separate provenance through retrieval, evaluation and answer generation.

## Verification

Before finalizing a material answer the system checks support, applicability, scope, version, freshness, conflicts and source provenance.

## Document flow

input → security → classifier/router → specialized extraction → normalized structure → metadata/versioning → structure-aware chunking → embeddings → Qdrant → retrieval/evidence → Orchestrator → verified response.

Large-document analysis is an Agent workflow using bounded retrieval or planned section-by-section processing.

## Operational layer

NVIDIA DGX Dashboard handles system-level monitoring and JupyterLab. Corporate AI Console handles application topology, health, dependencies, logs and resource state.

## Deployment

Declarative service definitions, persistent volumes, health checks, explicit networks, resource limits, version pinning and documented recovery.
