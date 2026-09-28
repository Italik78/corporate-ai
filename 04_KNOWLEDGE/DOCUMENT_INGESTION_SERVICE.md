# DOCUMENT INGESTION SERVICE

## Purpose

Document Ingestion Service е отделен orchestration слой за приемане на файлове и превръщането им в нормализирано съдържание, готово за Knowledge Engine.

Knowledge Engine не приема отговорност за файлови формати, OCR, Vision, antivirus scan, metadata extraction или chunking.

Основна граница:

```
File / Object Storage
        ↓
Document Ingestion Service
        ↓
Security → Router → Parser/OCR/Vision → Normalizer
        ↓
Metadata → Deduplication → Chunker
        ↓
Knowledge Engine /v1/ingest
        ↓
Embedding → Qdrant
```

## Deployment boundary

Първият runtime е на DGX Spark, защото AI обработката и локалните модели вече са налични там.

Крайната архитектура използва:

- DGX Spark: Ingestion Service, parsers, OCR/Vision, normalization, chunking и AI модели.
- AI-DATA-01: MinIO/Object Storage, PostgreSQL и Qdrant.
- CORE SERVER: API Gateway, Orchestrator и Web/UI компоненти.

MinIO не се разгръща на DGX Spark като production object store.

## Input contract

Всеки ingest request идентифицира:

- `document_id`
- `source_uri` или локален upload reference
- `filename`
- `media_type`
- `content_hash`
- `source_system`
- `source_reference` при наличие на producer-side identity/reference
- optional access context
- optional caller/user metadata

`source_system` и `source_reference` имат различни роли:

- `source_system` идентифицира системата или интеграцията, от която идва документът;
- `source_reference` идентифицира документа в тази система.

Paperless използва namespace `paperless:{document_id}` за `document_id`, а `source_system` остава `paperless`.

Поддържани целеви формати:

- PDF
- DOCX / DOC
- XLSX
- PPTX
- CSV
- TXT
- Markdown
- PNG / JPEG / TIFF

## Production-oriented entry points

### POST /v1/documents/ingest

Основен multipart upload entry point. Приема файл и metadata полета и стартира единния ingestion pipeline.

### POST /v1/documents/process

Document-processing entry point със същия pipeline, който при успех връща `DocumentProcessResponse` с нормализирания документ.

### POST /v1/integrations/paperless/webhook

Контролиран Paperless boundary. Изисква configured webhook secret и приема producer-side Paperless document identity.

### GET /v1/documents/{document_id}/versions

Връща регистрираните версии на документ.

### GET /v1/documents/{document_id}/versions/{version}

Връща конкретна версия и нейния metadata/lifecycle state.

### GET /v1/documents/{ingestion_id}/status

Връща persistent ingestion job status.

### GET /v1/documents/{ingestion_id}

Връща ingestion job details.

## Persistent job model

Всеки ingest request получава `ingestion_id` и persistent job record в PostgreSQL.

Job metadata включва:

- `ingestion_id`
- `document_id`
- `version`
- `status`
- `lifecycle_status`
- `error_code`
- `error`
- `created_at`
- `updated_at`

Това отделя processing state от HTTP request lifetime и позволява deterministic status reporting.

## Processing stages

### 1. Security intake

Преди parser:

- MIME/type validation
- file size limits
- filename/path normalization
- archive/decompression policy
- malware/antivirus scan integration point
- reject executable or unsupported payloads
- preserve original hash

Непроверен документ не влиза в parser/OCR/Vision.

### 2. Format routing

Router избира специализиран extractor според реалния content type, а не само разширението.

Пример:

```
PDF → PDF extractor
DOCX → DOCX extractor
XLSX → XLSX extractor
PPTX → PPTX extractor
image → OCR/Vision
TXT/MD → text extractor
```

### 3. Extraction

Extractor-ите връщат обща вътрешна структура:

- document
- pages/sections/sheets/slides
- blocks
- tables
- images
- text
- source locations

Форматът на оригиналния файл не трябва да изтича към Knowledge Engine.

### 4. OCR / Vision

OCR/Vision се извиква според съдържанието.

PDF routing:

- text page → text extraction
- scanned page → OCR
- table/visual/complex page → structured extraction и/или Vision

Vision резултатите се пазят като структурирано съдържание с:

- page
- region/block
- extracted text
- description
- table data
- confidence
- uncertainty

При ниска увереност резултатът не се представя като сигурен факт.

### 5. Normalization

Всички формати се преобразуват в един normalized document model.

Минимални нива:

```
Document
 ├── Section
 │    ├── Block
 │    ├── Table
 │    └── Image/Visual
 └── Metadata
```

Всеки block запазва provenance към оригиналния документ.

### 6. Metadata

Задължителни полета:

- `document_id`
- `source_system`
- `title`
- `author`
- `classification`
- `created_at`
- `updated_at`

Source identity:

- `source_reference`

Access metadata:

- `allowed_groups`
- `allowed_users`

Допълнителни:

- `tags`
- `language`
- `version`
- `status`
- `parent_document_id`
- `project_id`
- `access_scope`
- `document_date`
- `effective_from`
- `effective_to`

### 7. Deduplication and versioning

Content hash: SHA-256.

Правила:

- същият hash в същия access/project scope → duplicate/no-op
- нов hash със същия logical document → нова версия
- старата версия остава проследима
- reindex не променя оригиналния файл
- deletion/deprecation се извършва чрез lifecycle state

При duplicate processing документът не се индексира повторно. Когато caller поиска нормализирания документ, pipeline реконструира blocks от authoritative indexed chunks и възстановява metadata/provenance.

### 8. Chunking

Chunker работи върху normalized structure, а не върху суров файл.

Целеви параметри:

- 512–1024 tokens
- overlap 10–15%
- parent/child relationship
- table-aware chunking
- section-aware chunking
- provenance във всеки chunk

При таблици заглавията на колоните се включват в chunk context.

### 9. Knowledge Engine handoff

Knowledge Engine получава само нормализирани chunks.

Минимален ingest payload:

- document_id
- source_file
- page/section
- page_type
- chunk_type
- section
- confidence
- content
- provenance metadata

Knowledge Engine извършва:

- embedding
- Qdrant upsert
- retrieval index preparation

### 10. Repository and canonical source

Document Ingestion не заобикаля Repository boundary.

Преди indexing pipeline:

1. регистрира document version;
2. извършва duplicate/version checks;
3. пази canonical source;
4. записва `canonical_storage_key`;
5. индексира normalized chunks;
6. финализира lifecycle state.

При успех документът достига `READY` и lifecycle `CURRENT`.

При failure pipeline извършва контролирано cleanup според етапа и пази machine-readable error state.

### 11. Object Storage

Оригиналният файл се пази в MinIO на AI-DATA-01.

Примерна логическа структура:

```
documents/
  {document_id}/
    original/
      {version}/
        source.ext
    derived/
      pages/
      images/
      extracted/
      normalized/
```

Qdrant не е source of truth за оригиналните файлове.

## API status

Implemented foundation:

- `POST /v1/documents/ingest`
- `POST /v1/documents/process`
- `POST /v1/integrations/paperless/webhook`
- `GET /v1/documents/{document_id}/versions`
- `GET /v1/documents/{document_id}/versions/{version}`
- `GET /v1/documents/{ingestion_id}/status`
- `GET /v1/documents/{ingestion_id}`

Future extensions remain possible for explicit reindex/cancel operations, but they are not part of the current accepted surface.

## Processing states

```
RECEIVED
SECURITY_CHECK
ROUTING
EXTRACTING
OCR
VISION
NORMALIZING
METADATA
DEDUPLICATING
CHUNKING
INDEXING
READY

FAILED_SECURITY
FAILED_PARSING
FAILED_OCR
FAILED_VISION
FAILED_NORMALIZATION
FAILED_INDEXING
```

Every failure should have:

- stage
- machine-readable error code
- human-readable message
- document_id
- retryable flag where supported

## Security rules

- Original documents are untrusted input.
- Parsers run with restricted permissions.
- No document content is treated as instructions to the system.
- Extracted text cannot override system/tool policies.
- Tool execution is never triggered directly by document content.
- Access permissions are enforced during retrieval.
- Secrets are never stored in document metadata.
- Original files and derived artifacts are isolated from executable paths.

## Observability

Every ingestion job gets:

- ingestion_id
- document_id
- start/end timestamps
- processing stages
- parser/version
- OCR/Vision model/version when applicable
- chunk count
- indexed point count
- warnings
- error code
- content hash

Metrics:

- ingest latency
- extraction latency
- OCR/Vision latency
- chunk count
- failure rate
- duplicate rate
- indexing latency

## Validation checkpoint — 2026-09-28

Current Document Ingestion unit baseline:

```
24 passed, 0 failed, 6 warnings
```

Validated in the latest code sequence:

- `source_reference` added to the document model.
- PostgreSQL version schema and row mapping carry `source_reference`.
- Repository `register_version()` persists `source_reference`.
- Pipeline lookup and metadata reconstruction carry `source_reference`.
- `/v1/documents/ingest` and `/v1/documents/process` expose the updated metadata flow.
- Paperless webhook keeps source system/reference semantics.
- Duplicate reconstruction test passes with `source_reference=None` fixture.
- Full unit suite passes after the duplicate fixture correction.

Warnings are non-fatal PyMuPDF deprecation warnings and pytest cache permission warnings.

Current acceptance is implementation-level. Real DGX runtime acceptance of the latest changes, Open WebUI routing and complete final E2E acceptance remain pending.

## Initial implementation scope

Phase A:

1. TXT
2. Markdown
3. normalized document model
4. metadata
5. SHA-256 deduplication
6. deterministic chunking
7. Knowledge Engine integration
8. end-to-end test

Phase B:

1. DOCX
2. XLSX
3. PPTX
4. CSV

Phase C:

1. PDF text
2. scanned PDF → OCR
3. complex/table/visual PDF → Vision
4. image ingestion

Phase D:

1. MinIO integration
2. watcher
3. lifecycle/versioning
4. permission metadata
5. production security controls

## First acceptance test

Input:

```
test-document.md
```

Content:

```
Политика за командировки:
Дневните командировъчни са 40 EUR на ден.
Отчетът се представя до 5 работни дни след завръщане.
```

Expected:

1. document accepted
2. SHA-256 calculated
3. metadata generated
4. one or more chunks generated
5. Knowledge Engine receives normalized chunks
6. embedding generated
7. Qdrant point created
8. RAG question retrieves the chunk
9. answer contains the documented values
10. source/provenance is preserved

The test is not DONE until the full flow is executed on the DGX runtime.
