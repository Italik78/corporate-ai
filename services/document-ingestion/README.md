# Document Ingestion Service

First implementation scope: TXT/Markdown → normalized document → deterministic chunks → Knowledge Engine `/v1/ingest`.

## Run locally

    cd services/document-ingestion
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt
    pytest -q
    uvicorn app.main:app --host 0.0.0.0 --port 8095

## Docker

The service expects the Knowledge Engine on Docker network `ai-net` at `http://corporate-ai-knowledge-engine-0.3.1-test:8090`.
Override with `INGESTION_KNOWLEDGE_ENGINE_URL`.

## API

`POST /v1/documents/ingest` multipart form: `file`, optional `document_id`, optional `source_system`.
`GET /v1/documents/{ingestion_id}/status`
`GET /health`

This version intentionally supports only TXT/Markdown. DOCX/XLSX/PPTX/CSV/PDF/OCR/Vision are added after the first end-to-end acceptance test.
