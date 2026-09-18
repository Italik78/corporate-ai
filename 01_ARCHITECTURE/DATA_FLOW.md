# DATA FLOW

User → Open WebUI → Gateway/Agent → Router → LLM, Knowledge, Vision or Tools.

Document: file → classifier/router → extractor → normalized structure → chunker → embeddings → Qdrant/Graph → retrieval → grounded answer.

Tool: agent → policy → schema validation → tool → artifact → provenance/traceability.