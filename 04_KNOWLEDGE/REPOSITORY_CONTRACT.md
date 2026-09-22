# Corporate AI Repository Contract v0.1

## Purpose

The Repository is the canonical document storage boundary for Corporate AI.

It owns the authoritative relationship between:

- documents;
- document versions;
- canonical source files;
- folders/scopes;
- access control metadata;
- lifecycle state;
- provenance;
- repository audit events.

The Repository is independent from the Knowledge Engine.

Qdrant is a search/retrieval index only and is never the canonical document store.

## Architectural boundary

```text
Corporate AI Gateway / Agent
            |
            v
     Repository Contract
            |
      +-----+------+
      |            |
      v            v
 PostgreSQL    Object Storage
 metadata      canonical files
      |
      v
 Document Ingestion
      |
      v
 Knowledge Engine
      |
      v
    Qdrant
```

Repository implementations must be replaceable without changing the Knowledge Engine or Agent contracts.

## Canonical ownership

### Repository owns

- document identity;
- document versions;
- canonical source file;
- source file content hash;
- folder/scope membership;
- access scope / ACL metadata;
- lifecycle state;
- effective dates;
- document relationships;
- provenance;
- repository audit events.

### Document Ingestion owns

- security intake;
- format detection;
- extraction/OCR/Vision;
- normalization;
- structure-aware chunking;
- ingestion processing state;
- handoff of normalized chunks to Knowledge Engine.

Document Ingestion must not become the canonical document repository.

### Knowledge Engine owns

- embeddings;
- vector index;
- retrieval;
- evidence processing.

Knowledge Engine must not become the canonical document repository.

## Document identity

A document has a stable `document_id`.

A document version is identified by:

```text
document_id + version
```

Every version has:

- content hash;
- canonical source reference;
- metadata;
- lifecycle state;
- provenance;
- effective dates;
- relationship metadata.

A new content hash for an existing logical document creates a new version.

The same content hash for the same logical document is a duplicate/no-op.

## Lifecycle

The Repository lifecycle is:

```text
INGESTING
    |
    v
 CURRENT
    |
    v
 SUPERSEDED
    |
    v
 ARCHIVED
```

Lifecycle semantics:

- `INGESTING` — version is registered but processing is not complete.
- `CURRENT` — applicable current version.
- `SUPERSEDED` — replaced by a newer version.
- `ARCHIVED` — retained for history but not applicable for normal retrieval.

Lifecycle changes must be explicit and auditable.

Deletion must not silently remove the canonical record.

Physical deletion, when permitted by policy, is a separate repository operation with an audit trail.

## Repository operations

The minimum logical contract is:

### Create / ingest

Accept a source document and create or register a document version.

Required information:

- source system;
- filename;
- content hash;
- content or canonical object reference;
- document metadata;
- requested folder/scope;
- access metadata.

Result:

- `document_id`;
- `version`;
- canonical source reference;
- lifecycle state;
- content hash.

### Read metadata

Retrieve document or version metadata without requiring vector search.

### Read canonical content

Retrieve the canonical source file for an authorized caller.

### List versions

Return all known versions of a document in deterministic order.

### Move

Change folder/scope membership without changing document content or version identity.

### Update metadata

Change mutable metadata without creating a new content version unless policy explicitly requires it.

### Archive

Transition a version to `ARCHIVED`.

### Restore

Restore an archived version only when policy permits it.

### Delete

Delete/deprecate a document through an explicit lifecycle operation.

The operation must define what happens to:

- canonical source;
- derived artifacts;
- Knowledge Engine index;
- audit records.

### Access check

The Repository/policy boundary must be able to answer whether a caller may access:

- a document;
- a specific version;
- a folder/scope.

Semantic relevance must never bypass authorization.

## Folder and scope model

The Repository must support hierarchical logical scopes:

```text
Corporate Knowledge
├── Finance
│   ├── Policies
│   └── Procedures
├── HR
│   ├── Policies
│   └── Procedures
└── Procurement
    ├── Projects
    └── Standards
```

A document may belong to one or more logical scopes according to repository policy.

Scope identity must be stable and must not depend on display names.

`access_scope` in the current ingestion implementation is a compatibility field and is not considered a complete folder/ACL model.

## Access control

Authorization is enforced outside the LLM.

Repository metadata must support:

- allowed users;
- allowed groups;
- scope/folder permissions;
- document-level restrictions where required.

The Agent receives only evidence that has already passed authorization.

Document content, metadata and Vision output cannot grant themselves access.

## Canonical storage

The canonical source file must be stored outside Qdrant.

Target logical layout:

```text
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

The exact object-storage implementation is intentionally not fixed by this contract.

A repository adapter may use:

- S3-compatible object storage;
- MinIO;
- another approved object store;
- a controlled local storage adapter for development/testing.

The storage backend must be replaceable.

## Provenance

Every indexed chunk must be traceable to:

```text
repository document
    -> document version
        -> canonical source
            -> normalized structure
                -> chunk
```

Minimum provenance:

- document_id;
- version;
- source_file;
- content_hash;
- source location such as page/section/sheet/slide;
- chunk_id.

Generated artifacts must retain references to the source evidence used to create them.

## Knowledge Engine integration

Repository state is authoritative.

Knowledge Engine receives indexed representations of repository content.

For lifecycle changes:

- `CURRENT` content is retrievable when authorized;
- `SUPERSEDED` content is excluded from default current-state retrieval;
- `ARCHIVED` content is excluded from default retrieval;
- historical retrieval may explicitly request older versions.

Repository changes must be propagated to the Knowledge Engine.

Deleting/deprecating a document must not leave unauthorized or stale searchable evidence active.

## Audit

Repository operations must be auditable.

At minimum record:

- event_id;
- timestamp;
- actor/service;
- operation;
- document_id;
- version where applicable;
- previous state;
- new state;
- result;
- error code where applicable.

## Failure semantics

Repository operations must distinguish:

- validation failure;
- authorization failure;
- duplicate;
- version conflict;
- canonical storage failure;
- metadata persistence failure;
- index synchronization failure;
- transient dependency failure.

Failures must be machine-readable.

No operation may report success when canonical metadata and source storage are known to be inconsistent.

## Security requirements

Repository implementations must:

- treat uploaded files as untrusted;
- keep canonical files outside executable paths;
- prevent path traversal;
- enforce size/type policies;
- avoid storing secrets in document metadata;
- enforce authorization before content retrieval;
- provide deterministic audit information.

## Compatibility with current implementation

The existing Document Ingestion implementation already provides:

- PostgreSQL document version metadata;
- SHA-256 deduplication;
- lifecycle states;
- version relationships;
- project/access metadata;
- effective dates;
- Knowledge Engine lifecycle propagation.

These capabilities are preserved.

The Repository Contract formalizes the architectural boundary around them.

The implementation must not duplicate the existing lifecycle/version logic.

## Initial implementation strategy

Phase 1:

1. define repository interfaces/models;
2. adapt existing PostgreSQL metadata persistence behind the contract;
3. introduce a development canonical-storage adapter;
4. persist canonical source references;
5. keep existing ingestion behavior working;
6. add repository contract tests.

Phase 2:

1. real object storage;
2. hierarchical folders/scopes;
3. ACL enforcement;
4. repository audit events;
5. lifecycle-to-index synchronization;
6. delete/restore semantics.

Phase 3:

1. replaceable external repository adapter;
2. repository UI integration;
3. Open WebUI scope mapping.

## Non-goals of v0.1

This contract does not select a specific repository product.

It does not implement:

- Mayan EDMS;
- MinIO deployment;
- UI;
- full ACL engine;
- document watcher;
- repository search UI.

Those are implementation decisions made behind this contract.

## Acceptance criteria

The Repository Contract is considered implemented only when:

1. canonical source files have an authoritative storage location;
2. document/version metadata is persistent;
3. lifecycle transitions are deterministic;
4. repository access checks exist at the enforcement boundary;
5. Knowledge Engine is treated as an index;
6. provenance survives from source file to retrieved evidence;
7. delete/archive behavior is defined and tested;
8. failures are machine-readable;
9. repository implementation can be replaced without changing Agent/Knowledge Engine contracts;
10. the full path is validated on the DGX runtime.
