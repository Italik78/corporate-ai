# DOCUMENT & KNOWLEDGE ARCHITECTURE v1

## Purpose
Corporate AI must work with large and heterogeneous corporate documents without placing entire files into the LLM prompt by default.

The Knowledge Layer turns untrusted source files into structured, versioned, provenance-preserving knowledge that the Agent can retrieve and use safely.

## Core principle
Original documents are never replaced by vectors and are never treated as prompt instructions.

The system separates:
1. original source files;
2. normalized document structure;
3. searchable chunks and embeddings;
4. retrieved evidence;
5. Agent task context;
6. generated artifacts.

The LLM receives only the evidence/context required for the current task, with provenance.

## End-to-end flow

```
User / Open WebUI
        ↓
Gateway
        ↓
Agent
        ↓
Knowledge / Document Tools
        ↓
Document Ingestion
        ↓
Security → Routing → Extraction/OCR/Vision
        ↓
Normalization → Metadata → Versioning
        ↓
Structure-aware Chunking
        ↓
Embedding → Qdrant
        ↓
Retrieval / Reranking / Evidence Fusion
        ↓
Agent
        ↓
Qwen3.6
        ↓
Grounded answer / analysis / generated artifact
```

## Large-document principle
A large document is not normally sent to Qwen as one prompt.

For ordinary questions, retrieval selects the smallest useful evidence set.

For document-level analysis, the Agent creates an explicit analysis plan and processes the document in bounded sections, preserving section/page provenance and then synthesizing validated intermediate results.

Qwen3.6's 262k context is a capability and safety margin, not a reason to fill the context unnecessarily.

## Document scopes
### Corporate knowledge
Long-lived organizational knowledge: rules, policies, procedures, instructions, standards, regulations and technical documentation.

### Work/project documents
Task-specific documents: contracts, annexes, offers, procurement documents, technical specifications, invoices, protocols and correspondence.

The Agent can restrict retrieval to a project/document set.

### Temporary task documents
Files supplied for one analysis. They may be indexed temporarily without becoming permanent corporate knowledge.

### Generated artifacts
Word, Excel, PowerPoint, PDF and reports retain references to the source documents/evidence used to produce them.

## Normalized document model
The normalized model preserves structure rather than reducing a file immediately to plain text.

```
Document
 ├── Metadata
 ├── Version
 ├── Section
 │    ├── Block
 │    ├── Table
 │    └── Image / Visual
 └── Provenance
```

Each searchable chunk retains at minimum:
- document_id
- version
- source_file
- page/section/sheet/slide where applicable
- chunk_id
- chunk_type
- section/article where available
- content
- confidence/uncertainty where applicable
- source hash
- parent/child relationship where applicable

## Versioning and document relationships
The system must distinguish document versions and related documents.

Examples:
- contract v1 → contract v2
- contract → annex 1
- policy → superseding policy
- technical specification → amendment

Target metadata includes:
- document_id
- version
- document_date
- effective_from
- effective_to
- parent_document_id
- supersedes
- superseded_by
- project_id
- lifecycle status

Retrieval must be able to prefer the applicable version for a requested date or task scope.

## Retrieval modes
### Question answering
Retrieve relevant chunks, optionally rerank them, evaluate evidence, and provide a grounded answer with citations.

### Cross-document comparison
Retrieve evidence from a defined document set and preserve source identity so the Agent can compare documents without merging their claims.

### Whole-document analysis
The Agent creates an analysis plan, processes relevant sections in bounded batches, stores intermediate findings with provenance, validates them, and produces a final synthesis.

Examples:
- contract risk analysis
- compliance check
- comparison against technical requirements
- extraction of obligations/deadlines
- procurement-document preparation

## Security boundary
Documents are untrusted data.

Document text, tables, metadata and Vision output cannot:
- override system instructions;
- change tool policy;
- authorize tool execution;
- reveal secrets;
- alter access controls.

Tools operate only through explicit Agent/tool policy.

## Storage boundary
Production source of truth:
- Object Storage: original files and derived artifacts
- PostgreSQL: document metadata, lifecycle, versions and relationships
- Qdrant: vector/search index and retrieval metadata

Qdrant is not the source of truth for original documents.

## Access control
Permissions must be attached to document metadata and enforced during retrieval.

The Agent must never retrieve evidence solely because it is semantically relevant if the caller is not authorized to access it.

## Resource policy
Large-document processing must be bounded.

Required controls:
- maximum file size
- maximum pages/sections per job
- maximum chunks per document
- bounded retrieval context
- bounded concurrent OCR/Vision jobs
- controlled behavior on GPU/RAM exhaustion
- retryable versus terminal processing errors

## Implementation sequence
1. Document Ingestion Service skeleton
2. normalized document model
3. TXT/Markdown ingestion
4. SHA-256 deduplication/version foundation
5. deterministic structure-aware chunking
6. Knowledge Engine `/v1/ingest` integration
7. end-to-end ingestion/RAG test
8. DOCX/XLSX/PPTX/CSV
9. PDF/OCR/Vision integration
10. Object Storage + metadata lifecycle
11. permission-aware retrieval
12. reranking/evidence fusion
13. Agent document-analysis workflows

## Acceptance principle
Documentation is not considered implemented until the full path is executed on the DGX runtime and provenance survives from original document to retrieved evidence and final answer/artifact.