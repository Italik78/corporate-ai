# CHAT CONTEXT

Този файл е стартов контекст за нови разговори по Corporate AI.

Проектът е отделен от ZlaCloud.

## Визия

Изграждаме локална Corporate AI платформа върху NVIDIA DGX Spark GB10. Това не е ChatGPT clone. LLM е reasoning/generation engine, а контролът, знанието, паметта, инструментите и доказателствата са извън модела.

Основна логика:

User/API → Corporate AI Gateway → AI Agent/Orchestrator → Knowledge / Web Research / Tools / Document+Vision → Evidence/Provenance → Qwen3.6 → validation/citations → response

## Основен модел

Qwen3.6-35B-A3B-NVFP4 е primary production LLM.

Текущ runtime:
- context 262144
- GPU utilization 0.65
- KV FP8
- reasoning parser qwen3
- tool calling enabled
- qwen3_coder tool parser
- standard thinking disabled
- speculative MTP 3

Phase 1 допуска временно 128K context, за да се освободи ресурс за останалите компоненти. Runtime промяната трябва да се направи отделно и да се измери.

## Основни capabilities

- conversation
- short-term memory
- long-term conversation memory
- Project Memory
- long-running Task Memory/State
- Knowledge/RAG
- controlled Web Research
- Document Ingestion
- OCR/Vision
- Tools/Office
- Skills
- Prompt Registry
- Model Registry
- ACL/Policy
- Evidence/Provenance
- Audit
- Evaluation
- Open WebUI/API

## Memory

Memory е отделна capability.

Различаваме:
1. current conversation / short-term context
2. long-term conversation memory
3. project memory
4. durable long-running task state
5. optional user preference memory

Корпоративните документи не се превръщат автоматично в memory. Canonical knowledge остава в Document Repository.

## Context

Agent-ът не изпраща цялата история, целия проект или целия документ към Qwen.

Context Builder събира само релевантни:
- system/policy instructions
- current request
- recent turns
- summaries
- project memory
- task state
- Knowledge evidence
- Web evidence
- tool results
- skill/prompt instructions

## Knowledge

Qwen3-Embedding-4B → Qdrant → conditional CPU reranker → evidence fusion → grounded Qwen answer.

Qdrant е index, не source of truth.

Evidence:
- SUPPORTED
- CONFLICT
- INSUFFICIENT_EVIDENCE

## Web Research

Qwen няма unrestricted Internet.

Web Research Service прави:
- research planning
- search
- controlled fetch
- extraction
- source classification
- cross-check
- conflict detection
- provenance
- citation validation

Web content is untrusted input.

## Skills / Prompts / Models

Skills са versioned capability contracts.

Prompts са отделни versioned artifacts.

Models и runtime configurations се управляват чрез Model Registry.

Production versions са immutable и audit-able.

## Tasks

Long-running work е durable task:
- task_id
- owner/scope
- plan
- checkpoints
- events
- evidence
- artifacts
- retries
- cancellation
- result

## Security

ACL и policy се прилагат преди информацията да попадне в LLM context.

Documents и Web pages са untrusted input и не могат да override-ват system/tool policies.

## Scale-out

Първо доказваме целия продукт на един DGX Spark.

След benchmark:
- DGX nodes за LLM/Vision
- CPU nodes за reranking/ingestion/worker services
- data nodes за PostgreSQL/Object Storage/Qdrant
- application nodes за Gateway/Agent
- worker pools за research/tasks

Втори DGX не увеличава автоматично context window на една model instance.

## Working rule

При неизвестно се проверява, не се измисля.

GitHub Italik78/corporate-ai е source of truth.
