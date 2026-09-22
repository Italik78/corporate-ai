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
 + Evidence Research Gateway + Vision
       |      |      |      |
       +------+------+------+
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

## Data layer

- Document Repository/Object Storage — canonical files
- PostgreSQL — identity, memory, tasks, skills, prompts, audit
- Qdrant — vector retrieval index

## Runtime

Phase 1: all required services on DGX Spark with resource limits.

Future: Gateway/Agent, AI workers, CPU workers and data services distributed across multiple servers.

## User interface

Open WebUI is the primary workspace.

Corporate AI Console is operational/application topology, not a second chat product.

NVIDIA DGX Dashboard remains the system-level dashboard.
