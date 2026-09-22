# CORPORATE AI PLATFORM

## Purpose

Corporate AI is a local, secure and scalable corporate AI platform. It is not a ChatGPT clone and the LLM is not the source of truth.

The platform combines:
- conversational AI
- corporate knowledge and RAG
- controlled Web Research
- document intelligence and Vision
- tools and business-system integrations
- short-term and long-term memory
- project memory
- long-running task state
- versioned skills and prompts
- evidence, provenance and audit
- policy, ACL and human approval

The first complete deployment runs on one NVIDIA DGX Spark. The architecture is designed so components can later be distributed across multiple DGX and CPU/storage servers without changing the logical platform.

## Core principle

The LLM reasons over controlled context. It does not independently decide:
- what data a user may access
- which tools may execute
- what external sources are trusted
- whether unsupported information is a fact
- what should become persistent memory

Those decisions belong to platform services.

## Logical architecture

```
User / API / Automation
        |
        v
Corporate AI Gateway
(Auth, Identity, ACL, Policy, Session, Audit)
        |
        v
AI Agent / Orchestrator
(Plan, Context, Memory, Skills, Prompts, Tasks)
        |
        +----------------+----------------+----------------+
        |                |                |                |
        v                v                v                v
Knowledge          Web Research        Tools          Document/Vision
Repository         & Evidence          Gateway          Pipeline
        |                |                |                |
        +----------------+----------------+----------------+
                         |
                         v
                   Evidence Layer
          SUPPORTED / CONFLICT /
          INSUFFICIENT_EVIDENCE
                         |
                         v
                     Qwen3.6
                         |
                         v
          Validation / Citations / Provenance
                         |
                         v
                    Final response
```

## Platform capabilities

### 1. Conversation
- current-turn context
- selected recent conversation history
- automatic conversation summarization
- durable conversation memory
- user-visible conversation history
- context-budget management

### 2. Memory
Memory is separated by scope and lifecycle:
- short-term conversation memory
- long-term conversation memory
- project memory
- long-running task memory/state
- user preference/profile memory where explicitly allowed
- organizational knowledge remains in the Knowledge Repository, not memory

Memory must be:
- scoped
- permission-aware
- provenance-aware
- versioned where applicable
- inspectable
- deletable
- excluded from context unless relevant

### 3. Skills
A skill is a versioned capability definition, not an uncontrolled prompt.

A skill contains:
- purpose
- trigger/selection rules
- required inputs
- allowed tools
- prompt references
- policies
- dependencies
- output contract
- validation rules
- version
- lifecycle state

### 4. Prompt Registry
Prompts are managed separately from skills.

Prompt records are:
- versioned
- named
- environment-aware
- tested
- auditable
- referenced by model/skill/task configuration

Prompt content from untrusted documents or Web pages never overrides system policy.

### 5. Long-running tasks
Tasks are durable jobs with:
- task_id
- owner
- project/session scope
- plan
- state
- checkpoints
- events
- artifacts
- evidence
- retries
- cancellation
- result

Tasks may continue after the chat request ends.

### 6. Knowledge
The Knowledge Repository is the source of truth for corporate documents. Qdrant is a retrieval index.

Flow:
Repository → Ingestion → normalized content → embeddings → Qdrant → retrieval → evidence → Qwen3.6.

### 7. Web Research
Web access is a controlled capability. Qwen3.6 does not receive unrestricted Internet access.

Research uses:
- query planning
- source discovery
- primary-source preference
- controlled fetching
- extraction
- source metadata
- cross-checking
- conflict detection
- provenance
- evidence assessment

### 8. Tools
Tools execute outside the LLM and are protected by:
- schema validation
- policy
- ACL
- approval where required
- timeout/resource limits
- audit
- provenance

### 9. Evidence
Evidence is a common layer for both internal knowledge and Web Research.

Minimum states:
- SUPPORTED
- CONFLICT
- INSUFFICIENT_EVIDENCE

The system must not silently choose a winner between conflicting sources.

### 10. Security
Security boundaries are enforced before information reaches the LLM:
- identity
- ACL
- tenant/project scope
- document permissions
- tool permissions
- network policy
- secrets
- audit
- untrusted-input isolation

## Data ownership

- Repository: original documents and versions
- Object storage: binary/derived artifacts
- PostgreSQL: identities, metadata, memory, tasks, skills, prompts, audit and application state
- Qdrant: vector retrieval index
- Evidence records: claims, sources, provenance and validation state
- LLM: transient reasoning/generation, not durable truth

## Deployment model

Phase 1:
- one DGX Spark
- all required services co-located where resource limits permit

Scale-out:
- LLM workers on DGX nodes
- CPU services on CPU nodes
- PostgreSQL/object storage/Qdrant on data nodes
- Gateway/Agent on application nodes
- independent worker pools for ingestion, research and long-running tasks

The logical APIs and contracts remain stable during scale-out.

## Quality requirement

A feature is not considered complete because the service starts. It must be validated end-to-end with representative tests and measurable acceptance criteria.
