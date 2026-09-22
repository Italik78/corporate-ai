# SERVICES

## Core AI

- qwen3.6 — primary LLM
- qwen3_embedding_4b — embeddings
- qdrant — vector index
- qwen3-reranker-cpu — conditional reranking

## Platform

- corporate-ai-gateway — controlled API entry
- agent/orchestrator — planning and capability coordination
- knowledge-engine — retrieval/evidence/grounded answer boundary
- evidence-engine — evidence states and claims
- document-ingestion — universal file processing
- web-research — controlled external research
- task-engine — durable long-running tasks
- memory service/store — scoped memory
- skill registry — versioned skills
- prompt registry — versioned prompts
- tool gateway — controlled tool execution

## User and application

- open-webui — primary user workspace
- corporate-ai-console — application topology/health
- caddy — reverse proxy/SSE where required

## Data

- document repository/object storage — canonical files and versions
- PostgreSQL — application state, identity, memory, tasks, skills, prompts, audit
- Qdrant — retrieval index

## Operational

- monitoring/metrics/logging
- backup/recovery
- evaluation/benchmarking

## Experimental

Alternative LLMs and model variants remain lab inventory until a benchmark demonstrates a production need.

## Deployment rule

Each service must have:
- clear responsibility
- version
- health check
- persistent storage where required
- configuration
- dependencies
- resource limits
- logging
- recovery procedure

Do not rebuild/remove existing services without configuration/data inventory.
