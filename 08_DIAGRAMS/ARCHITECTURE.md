# ARCHITECTURE DIAGRAM

User
↓
Open WebUI
↓
Corporate AI Gateway
↓
AI Orchestrator / Mind
├── Conversation Context
├── Task Understanding
├── Clarification
├── Planning / Decomposition
├── Corporate Knowledge
│   ├── Retrieval
│   ├── Reranking
│   └── Evidence / Provenance
├── Web Research
│   ├── Search
│   ├── Fetch
│   └── Web Evidence
├── Document Analysis
├── Controlled Tools
├── Verification
└── Qwen3.6

Source classes remain separated:
- Corporate
- Web
- Tool/API

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
AI Orchestrator
↓
Verification
↓
Qwen3.6
↓
Grounded Answer + Provenance

Web Research Flow

AI Orchestrator
↓
Web Search Gateway
↓
Search / Fetch
↓
Normalized Web Evidence
↓
Evidence Evaluation
↓
AI Orchestrator
↓
Verified Answer + Web Provenance

Large documents are processed through bounded retrieval or planned section-by-section analysis. Original files remain outside Qdrant.

Paperless-ngx integrates through a controlled webhook boundary; Tika/Gotenberg handle Office extraction/conversion before Document Ingestion.

Infrastructure: DGX Spark → NVIDIA Container Runtime → services on ai-net.

Operational: NVIDIA DGX Dashboard + Corporate AI Console.
