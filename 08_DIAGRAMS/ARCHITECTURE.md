# ARCHITECTURE DIAGRAM

User
↓
Open WebUI
↓
Corporate AI Gateway / Agent
├── Qwen3.6
├── Knowledge: Embedding, Qdrant, Reranker, Knowledge Graph
├── Vision
└── Tools: Word, Excel, PowerPoint, PDF

Infrastructure: DGX Spark → NVIDIA Container Runtime → services on ai-net.

Operational: NVIDIA DGX Dashboard + Corporate AI Console.