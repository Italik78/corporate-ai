# ARCHITECTURE DIAGRAM

```
USER / API / AUTOMATION
          |
          v
+---------------------------+
| Corporate AI Gateway      |
| Auth / ACL / Policy       |
| Session / Audit / Tasks   |
+-------------+-------------+
              |
              v
+---------------------------+
| AI Agent / Orchestrator   |
| Plan / Context / Memory   |
| Skills / Prompts / Tasks  |
+------+------+------+------+ 
       |      |      |      |
       v      v      v      v
 Knowledge   Web    Tools  Document
 + Evidence Research Gateway Ingestion
       |      |      |       |
       |      |      |       v
       |      |      |  +-----------+
       |      |      |  | Metadata  |
       |      |      |  | Version   |
       |      |      |  | Dedup     |
       |      |      |  +-----+-----+
       |      |      |        |
       |      |      |        v
       |      |      |  normalized chunks
       +------+------+--------+
              |
              v
       +-------------+
       |   Evidence  |
       | Supported   |
       | Conflict    |
       | Insufficient|
       +------+------+
              |
              v
          Qwen3.6
              |
              v
   Validation / Provenance
              |
              v
          RESPONSE
```

## Document Ingestion boundary

Document Ingestion is a separate service responsible for the controlled transition from an incoming file to normalized document/version data and downstream indexing.

Current responsibilities:
- accept supported document files
- persist ingestion metadata
- register document identity and version
- calculate and use content hash for duplicate/version detection
- preserve canonical document reference
- normalize extracted content into blocks/chunks
- pass normalized content to downstream Knowledge Engine/indexing
- persist controlled failure status and error code
- support lifecycle/version propagation

Current implementation checkpoint:
- PostgreSQL metadata/version persistence is active.
- Duplicate lookup uses psycopg `dict_row`.
- Duplicate-specific unit test passes.
- Application compilation, image rebuild and container startup pass.
- Real XLSX processing completes metadata registration, canonical storage, chunking, Knowledge Engine indexing and lifecycle finalization.
- The earlier `DocumentVersionResponse.tags` error was traced to a pre-restart runtime record; current source and runtime code match.
- No `tags` field was added to `DocumentVersionResponse` as a workaround.

Acceptance evidence: ingestion `6e220d34-abd9-46d0-99e5-befe4c97c4b0` is `READY`; document version `v1` is `CURRENT`; Knowledge Engine search returns indexed chunks for the document.

## Data layer

- Document Repository/Object Storage — canonical files
- PostgreSQL — document identity/version metadata, memory, tasks, skills, prompts, audit
- Qdrant — vector retrieval index

## Runtime

Phase 1: all required services on DGX Spark with resource limits.

Future: Gateway/Agent, AI workers, CPU workers and data services distributed across multiple servers.

## User interface

Open WebUI is the primary workspace.

Corporate AI Console is operational/application topology, not a second chat product.

NVIDIA DGX Dashboard remains the system-level dashboard.
