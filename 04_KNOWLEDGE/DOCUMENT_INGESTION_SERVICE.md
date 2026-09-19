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
- optional access context
- optional caller/user metadata

Поддържани целеви формати:

- PDF
- DOCX / DOC
- XLSX
- PPTX
- CSV
- TXT
- Markdown
- PNG / JPEG / TIFF

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

Access metadata:

- `allowed_groups`
- `allowed_users`

Допълнителни:

- `tags`
- `language`
- `version`
- `status`
- `parent_document_id`

### 7. Deduplication and versioning

Content hash: SHA-256.

Правила:

- същият hash → duplicate/no-op
- нов hash със същия logical document → нова версия
- старата версия остава проследима
- reindex не променя оригиналния файл
- deletion/deprecation се извършва чрез lifecycle state

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

### 10. Object Storage

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

## API

Планиран минимален API:

### POST /v1/documents/ingest

Приема документ и стартира ingestion.

### GET /v1/documents/{document_id}

Връща lifecycle/status metadata.

### GET /v1/documents/{document_id}/status

Връща текущия processing stage и errors.

### POST /v1/documents/{document_id}/reindex

Стартира повторна normalization/chunking/index операция.

### POST /v1/documents/{document_id}/cancel

Спира pending/running ingestion job при безопасно състояние.

Първата implementation версия не изисква всички endpoints.

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

Всеки failure трябва да има:

- stage
- machine-readable error code
- human-readable message
- document_id
- retryable flag

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
