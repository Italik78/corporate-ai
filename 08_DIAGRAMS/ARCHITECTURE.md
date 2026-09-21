# ARCHITECTURE DIAGRAM

User
↓
Open WebUI
↓
Corporate AI Gateway
↓
Agent
├── Task understanding / planning
├── Tool Policy / approval
├── Knowledge & Document Tools
│   ├── Document Ingestion
│   ├── Retrieval / Reranking
│   └── Evidence / Provenance
├── Qwen3.6
└── Office / File Tools

Document Knowledge Flow

Original File / Object Storage
↓
Paperless / Upload / API
↓
Document Ingestion
↓
Security
↓
Router
↓
Parser / OCR / Vision
↓
Normalized Document Model
↓
Metadata / Versioning
↓
Structure-aware Chunking
↓
Embedding
↓
Qdrant
↓
Retrieval / Evidence
↓
Agent Context
↓
Qwen3.6

Large documents are processed through bounded retrieval or planned section-by-section analysis. Original files remain outside Qdrant.

Paperless-ngx integrates through a controlled webhook boundary; Tika/Gotenberg handle Office extraction/conversion before Document Ingestion.

Infrastructure: DGX Spark → NVIDIA Container Runtime → services on ai-net.

Operational: NVIDIA DGX Dashboard + Corporate AI Console.