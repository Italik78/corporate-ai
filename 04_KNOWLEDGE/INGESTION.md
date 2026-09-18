# INGESTION

Supported: PDF, DOCX, DOC, XLSX, PPTX, CSV, TXT, images.

Pipeline: universal ingest orchestrator → format router → specialized extractor → normalized structure → chunker → embedder → Qdrant/Graph.

Metadata: chunk_id, chunk_type, source file, page, page type, section, confidence, plus document-specific structure.

XLSX is chunked as markdown tables in the latest known implementation. Watcher ingests new files from watcher-inbox. Chat attachments trigger ingestion before response where configured.