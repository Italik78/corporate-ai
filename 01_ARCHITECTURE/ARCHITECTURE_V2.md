# ARCHITECTURE V2

Open WebUI → Corporate AI Gateway → Intent/Task Router → Qwen3.6 / Knowledge / Tools / Vision.

Knowledge: query → embedding → parallel retrieval → metadata filtering → vector/keyword/graph evidence → conditional reranking → evidence fusion → context builder → Qwen3.6 → grounded response + sources.

Agent: Qwen3.6 → Agent Controller → Tool Gateway → validated tools. Every tool has schema, policy, validation, logging and traceability.

Document flow: input → classifier/router → specialized extraction → normalized structure → chunking → metadata → embeddings → Qdrant/Graph.

Operational layer: NVIDIA DGX Dashboard handles system-level monitoring and JupyterLab. Corporate AI Console handles application topology, health, dependencies, logs and resource state.

Deployment: declarative service definitions, persistent volumes, health checks, explicit networks, resource limits, version pinning and documented recovery.