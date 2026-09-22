# PROJECT MASTER

## Цел

Изграждане на локална, сигурна и мащабируема Corporate AI платформа върху NVIDIA DGX Spark GB10.

Corporate AI не е ChatGPT clone. Той комбинира conversational AI, корпоративно Knowledge/RAG, контролирано Web Research, document intelligence и Vision, Tools и интеграции, памет, Project Memory, Long-running Tasks, Skills, Prompt Registry, Evidence, Provenance, Audit, ACL, Policy и Human Approval.

Основният LLM е reasoning/generation engine, а не source of truth.

## База

- NVIDIA DGX Spark GB10
- 128 GB unified memory
- 4 TB NVMe
- Ubuntu 24.04.x LTS
- NVIDIA Driver 580.x
- CUDA 13.x
- Docker + NVIDIA Container Toolkit
- Docker network: ai-net

## Основен LLM

Qwen3.6-35B-A3B-NVFP4 чрез vLLM.

Текуща runtime конфигурация:
- served name: qwen36
- port: 8000
- context: 262144
- GPU utilization: 0.65
- KV cache: FP8
- reasoning parser: qwen3
- tool calling: enabled
- tool-call-parser: qwen3_coder
- thinking: disabled за стандартния режим
- speculative MTP: 3

Архитектурно Phase 1 допуска временно намаляване на context към 128K с цел ресурс за цялата платформа. Runtime промяната се прави отделно и се валидира измеримо.

## Основна архитектура

User/API → Corporate AI Gateway → AI Agent/Orchestrator → Knowledge / Web Research / Tools / Document & Vision → Evidence → Qwen3.6 → validation/provenance → response.

Gateway контролира identity, ACL, policy, session, audit и task submission.

Agent управлява planning, context, memory, skills, prompts, retrieval, research, tools и long-running tasks.

## Основни подсистеми

- Qwen3.6 primary LLM
- local embeddings
- Qdrant
- CPU reranker
- Knowledge Engine
- Evidence Engine
- Document Repository abstraction
- Document Ingestion
- PDF/OCR/Vision
- Web Research
- Agent/Orchestrator
- Gateway
- Memory
- Task Engine
- Skill Registry
- Prompt Registry
- Office/Tool Gateway
- Open WebUI
- Corporate AI Console
- provenance/audit
- monitoring
- backup/recovery
- evaluation

## Memory

Memory е отделна capability и не е скрито състояние в LLM context.

Поддържаме:
- short-term conversation memory
- long-term conversation memory
- project memory
- long-running task state/memory
- user preference memory при разрешен policy scope

Корпоративните документи остават в Knowledge Repository, а не в conversation memory.

## Long-running tasks

Дългите операции са durable tasks с task_id, owner/scope, plan, state, checkpoints, events, evidence, artifacts, retries, cancellation и result.

## Skills и Prompts

Skills са versioned capability contracts.

Prompts са отделни versioned artifacts в Prompt Registry.

И двете имат lifecycle, permissions, dependencies, tests и audit. Production versions са immutable.

## Knowledge / Evidence

Документите са недоверени входове.

Qdrant е retrieval index, не source of truth.

Evidence states:
- SUPPORTED
- CONFLICT
- INSUFFICIENT_EVIDENCE

LLM не избира тихо между конфликтни източници.

## Web Research

Web Research е контролирана capability. Qwen3.6 няма unrestricted Internet access.

Резултатът трябва да е source-linked и provenance-aware, с отделяне на факти, атрибутирани твърдения, inference, конфликти и липса на доказателства.

## Deployment strategy

Phase 1: целият функционален stack на един DGX Spark, с ресурсни ограничения.

След доказване на ефективността:
- LLM workers → DGX nodes
- CPU services → CPU nodes
- data → dedicated storage/database nodes
- gateway/agent → application nodes
- ingestion/research/tasks → worker pools

Логическите API и service contracts трябва да позволят scale-out без преработка на продукта.

## Source of truth

GitHub repository Italik78/corporate-ai е source of truth за архитектурата, конфигурацията, кода и документацията.

## Принцип

При неизвестно се проверява, не се измисля.

Функционалност се счита за готова само след реална техническа валидация и acceptance test.
