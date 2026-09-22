# CORPORATE AI — BUILD MASTER
**Checkpoint:** 2026-09-22

## 1. Purpose

This is the operational build map for the Corporate AI project.

The goal is a local, secure, evidence-grounded corporate AI platform that can:
- converse in Bulgarian and other languages;
- remember conversations and projects;
- work on documents and images;
- answer from corporate knowledge with evidence;
- perform controlled Internet research and return source-backed results;
- execute tools and business workflows under policy;
- run long tasks that survive interruption;
- generate Office/PDF artifacts;
- use reusable Skills and versioned Prompts;
- maintain provenance, audit and ACL;
- scale from one DGX Spark to a multi-server AI platform.

Core principle:

> When evidence is missing, the system verifies or says that evidence is insufficient. It must not invent.

## 2. Target architecture

```
USER / API / AUTOMATION
          |
          v
Corporate AI Gateway
(Auth / Identity / ACL / Policy / Session / Audit)
          |
          v
AI Agent / Orchestrator
(Planning / Context / Memory / Skills / Prompts / Tasks)
          |
    +-----+------+--------+---------+
    |            |        |         |
 Knowledge    Web       Tools    Documents
 + Evidence   Research  Gateway  + Vision
    |            |        |         |
    +------------+--------+---------+
                 |
                 v
        Evidence / Provenance
                 |
                 v
              Qwen3.6
                 |
                 v
       Validation / Citations
                 |
                 v
              RESULT
```

Canonical data:
- Document Repository/Object Storage = original documents and versions.
- PostgreSQL = application state, identity, memory metadata, tasks, skills, prompts, audit.
- Qdrant = retrieval index, never canonical storage.

## 3. What is already built/validated

### Hardware/runtime
- NVIDIA DGX Spark GB10.
- 128 GB unified memory, 4 TB NVMe.
- Ubuntu 24.04.x aarch64.
- NVIDIA driver/CUDA/Docker/NVIDIA Container Toolkit.
- Internal Docker network `ai-net`.
- DGX Dashboard operational.

### Primary LLM
Qwen3.6-35B-A3B-NVFP4 through vLLM.
Validated/current:
- served name qwen36;
- 256K context currently configured;
- GPU memory utilization 0.65;
- KV FP8;
- reasoning parser;
- tool calling;
- MTP 3;
- Vision requests.

A temporary 128K context configuration is an accepted Phase-1 optimization but has not yet been applied.

### Retrieval
- Qwen3-Embedding-4B local service.
- 2560-dimensional embeddings.
- Qdrant production collection `corporate_knowledge`.
- Knowledge Engine health/search/ingest/query.
- grounded RAG.
- controlled no-answer for insufficient evidence.
- deliberate conflicting evidence retrieval.
- Evidence Engine states: SUPPORTED / CONFLICT / INSUFFICIENT_EVIDENCE.
- CPU Qwen3 reranker is an intentional component because unified memory/GPU capacity is constrained.

### Document intelligence
Validated foundation:
- PDF classifier/router/preprocessor.
- Qwen3.6 Vision adapter.
- structured Vision JSON.
- TABLE/VISUAL/COMPLEX page handling.
- native PDF extraction with provenance.
- PDF → chunks → embeddings → Qdrant end-to-end.

Universal Document Ingestion service exists and is being expanded.

### Platform foundations
Architecture and partial implementation exist for:
- Corporate AI Gateway;
- Agent/Orchestrator;
- Web Research;
- Memory;
- Skills;
- Prompt Registry;
- Task Engine;
- Tool Gateway;
- Office Tools;
- Corporate AI Console;
- provenance/audit;
- model registry;
- scale-out.

These are architecture baselines unless explicitly marked validated/implemented.

## 4. What remains

### P0 — must work before the complete demonstration

1. **Document Repository**
   - choose and integrate the repository;
   - folders/subfolders;
   - users/groups/ACL;
   - versions;
   - delete/move/update events;
   - canonical file storage;
   - lifecycle events to ingestion/Qdrant;
   - prove deleted documents disappear from retrieval.

2. **Universal Document Ingestion**
   - PDF/DOCX/DOC/XLSX/PPTX/CSV/TXT/Markdown/images;
   - extraction/OCR/Vision;
   - tables and visual grounding;
   - metadata;
   - chunking;
   - embeddings;
   - provenance;
   - async jobs;
   - repository lifecycle synchronization.

3. **Gateway**
   - authentication/identity;
   - ACL/policy;
   - session handling;
   - OpenAI-compatible API;
   - streaming;
   - request budgets;
   - audit;
   - routing to Agent.

4. **Agent/Orchestrator**
   - intent classification;
   - planning;
   - capability selection;
   - context assembly;
   - memory access;
   - knowledge retrieval;
   - Web Research;
   - tool execution;
   - task creation;
   - final validation.

5. **Memory**
   - short-term conversation;
   - long-term conversation;
   - Project Memory;
   - task memory/state;
   - optional user preferences;
   - scope/ACL;
   - provenance;
   - deduplication;
   - deletion;
   - memory poisoning protection.

6. **Skills + Prompts**
   - registry;
   - versioning;
   - dependencies;
   - permissions;
   - test cases;
   - activation;
   - rollback;
   - immutable production versions.

7. **Long-running Tasks**
   - durable task DB;
   - checkpoints;
   - workers;
   - retry/idempotency;
   - cancellation;
   - human approval;
   - artifacts;
   - result API.

8. **Controlled Web Research**
   - search provider abstraction;
   - controlled fetch;
   - extraction;
   - source quality metadata;
   - primary-source preference;
   - cross-checking;
   - conflict handling;
   - citations;
   - prompt-injection isolation;
   - long-running research.

9. **Tool Gateway**
   - tool registry;
   - JSON schemas;
   - policy;
   - ACL;
   - approval;
   - timeouts;
   - sandboxing;
   - audit;
   - Office tools.

10. **Evaluation**
   - factuality;
   - groundedness;
   - citation correctness;
   - Web Research accuracy;
   - memory isolation;
   - tool correctness;
   - task recovery;
   - latency/concurrency/resource benchmarks.

### P1 — production hardening

- monitoring/metrics/tracing;
- backup/recovery;
- secret management;
- image/version pinning;
- CI/CD;
- security testing;
- prompt-injection test suite;
- load/concurrency tests;
- failure injection;
- data retention policies;
- admin UI;
- user/project management;
- artifact lifecycle.

### P2 — scale-out

After acceptance on one Spark:
- second DGX Spark;
- LLM/Vision worker distribution;
- CPU worker pool;
- dedicated PostgreSQL/object storage/Qdrant;
- Gateway/Agent application nodes;
- scheduling;
- service discovery;
- multi-node observability;
- horizontal concurrency.

A second DGX increases available compute/concurrency; it does not automatically increase one model instance's context window.

## 5. Definition of done

The project is ready for demonstration when a user can say, for example:

> "Направи проучване в интернет за X, провери информацията от няколко надеждни източника, отдели потвърдените факти от спорните твърдения, дай ми източници и ако има противоречия ги покажи."

The system must:
1. create a plan;
2. search via the controlled Web Research service;
3. fetch and sanitize sources;
4. preserve source URLs/metadata;
5. cross-check claims;
6. detect conflicts;
7. distinguish evidence from inference;
8. cite claims;
9. avoid unsupported conclusions;
10. save the research artifact;
11. keep task/provenance/audit state.

The same platform must then be able to continue with a corporate-document question, memory, tool execution and document generation.

## 6. How to use the build prompts

Each `BUILD_PROMPTS/*.md` file is an execution prompt for a strong coding/reasoning model.

Recommended loop:
1. Give the model the relevant prompt.
2. Also give it the repository and current branch.
3. Instruct it to inspect existing implementation before changing anything.
4. It must follow the project's canonical docs.
5. It must implement, test, document and report.
6. It must not silently change architecture.
7. It must commit its changes to a dedicated branch.
8. Review/merge only after tests pass.
9. Update CURRENT_STATUS/ROADMAP only with verified facts.

The prompts are intentionally written so they can be used with Claude, Gemini, DeepSeek, Kimi or another strong coding model.

## 7. Build order

Recommended order:
1. Repository + lifecycle contract
2. Universal Document Ingestion
3. Gateway
4. Agent/Orchestrator
5. Memory
6. Skills + Prompt Registry
7. Task Engine
8. Tool Gateway + Office
9. Web Research
10. End-to-end integration
11. Evaluation/benchmark
12. Production hardening
13. Scale-out

Do not parallelize components that depend on an unfinished contract unless the interface is explicitly frozen first.
