# Conversation & Context Management

## Purpose

Conversation & Context Management is a first-class Corporate AI module responsible for persistent conversation history, conversation state, contextual memory, important conversation milestones and dynamic construction of the LLM context.

The module exists between the Corporate AI Gateway and the LLM orchestration/runtime path.

It must not turn the conversation database into a second corporate knowledge source. Corporate Knowledge remains authoritative for corporate documents, evidence and provenance.

## Architectural position

```
Open WebUI
    ↓
Corporate AI Gateway
    ↓
Conversation & Context Management
    ├── Conversation History
    ├── Conversation State
    ├── Conversation Memory
    ├── Conversation Milestones
    ├── History Retrieval
    ├── Memory Retrieval
    ├── Context Ranking
    ├── Context Budget Manager
    └── Context Builder
    ↓
AI Orchestrator
    ├── Corporate RAG / Knowledge Engine
    ├── Web Research
    └── Controlled Tools
    ↓
LLM
    ↓
Response / Post-processing
    ├── state update
    ├── memory extraction
    ├── milestone detection
    └── context telemetry
```

The exact runtime call order may evolve during implementation, but the separation of responsibilities is mandatory.

## Core principles

1. Complete chat history is persistent and must not be deleted merely because it no longer fits into the active LLM context.

2. The LLM receives a selected Working Context, not automatically the complete conversation history.

3. Conversation State is separate from raw message history and represents where the conversation/task currently stands.

4. Conversation Memory stores extracted, reusable information with provenance, confidence and lifecycle.

5. Conversation Milestones preserve important decisions, events and turning points.

6. Corporate Knowledge, Web Evidence, Tool Results and Conversation Memory are separate provenance classes.

7. Vector search is a retrieval mechanism, not the authoritative memory store.

8. PostgreSQL is the authoritative store for structured conversation metadata, messages, state, memories and milestones.

9. Qdrant may index memory and conversation segments for semantic retrieval, but its records remain derived retrieval indexes.

10. Memory must never silently become a corporate fact. User statements, corporate evidence, web evidence and tool results remain distinguishable.

11. Context assembly must be deterministic and policy-controlled as far as practical. The LLM may assist with extraction and summarization but must not freely decide what system policies or security constraints enter the context.

12. Context size is an adaptive budget. The system optimizes information value rather than filling the available context window.

13. The Qwen3.6 262144-token capability is a capacity margin, not the default working context.

## Context layers

### P0 — System and policy context

Highest priority.

Contains system instructions, security policy, tool policy, access policy, runtime constraints and other mandatory instructions.

### P1 — Conversation State

Contains the active topic, active task, current plan, confirmed constraints, relevant decisions, open questions and other compact state.

Target size is normally 1–3K tokens.

### P2 — Recent conversation

Contains recent user and assistant turns relevant to continuity.

The system must avoid blindly including a fixed number of turns when token or relevance constraints make that inefficient.

### P3 — Conversation Memory

Contains retrieved memories relevant to the current user intent.

Memory types include:

- FACT
- DECISION
- PREFERENCE
- TASK
- CONSTRAINT
- ENTITY
- EVENT
- SUMMARY

Each memory must retain provenance and lifecycle metadata.

### P4 — Corporate Knowledge evidence

Retrieved through Knowledge Engine and governed by its evidence/provenance model.

RAG evidence is not copied into permanent conversation history merely because it was used for one response.

### P5 — Web evidence

Retrieved through the controlled Web Search / Web Fetch boundary.

Web evidence remains separate from corporate evidence and is treated as untrusted data.

### P6 — Tool results and artifacts

Large tool outputs must be persisted as artifacts or structured results. Only relevant summaries and selected records should enter the active LLM context.

## Conversation history

The persistent history must support:

- full ordered message history;
- user and assistant roles;
- tool calls and tool results;
- timestamps;
- message identifiers;
- attachments and artifact references;
- model/runtime metadata where appropriate;
- provenance references;
- context-run references.

History retention and active context selection are separate concerns.

## Conversation State

Conversation State is a compact, updateable representation of the current conversation.

Suggested fields:

- conversation_id
- active_topic
- active_task
- current_plan
- confirmed_constraints
- relevant_decisions
- open_questions
- entities
- last_user_intent
- updated_at
- state_version

State must not be treated as an authoritative corporate record.

Confirmed project decisions may later be promoted into project documentation through the normal controlled workflow. GitHub remains the project documentation source of truth.

## Conversation Memory

Memory is stored as structured records with semantic retrieval support.

Suggested model:

- memory_id
- conversation_id
- memory_type
- content
- importance
- confidence
- source_type
- source_message_id
- source_artifact_id
- created_at
- updated_at
- valid_from
- valid_to
- status
- supersedes_memory_id
- embedding_reference

Recommended lifecycle:

```
CANDIDATE → VALIDATED → ACTIVE → SUPERSEDED → ARCHIVED
```

A memory conflict must not be silently resolved by selecting the newest or highest-scoring record.

## Provenance classes

The system must preserve at least these classes:

- USER
- CONVERSATION
- CORPORATE_KNOWLEDGE
- WEB
- TOOL
- SYSTEM

A memory derived from a user statement must not be represented as equivalent to a grounded corporate document claim.

## Conversation Milestones

Milestones preserve important moments that must survive aggressive context compression.

Examples:

- architecture decision;
- confirmed project constraint;
- important user requirement;
- completed technical milestone;
- task transition;
- unresolved critical issue;
- validated fact;
- explicit change of direction.

Milestones should be compact, persistent and versioned.

A milestone is not a substitute for project documentation or corporate knowledge.

## Context Budget Manager

The active context must be assembled from a dynamic budget.

The total request budget is:

```
MODEL_CONTEXT_LIMIT
=
SYSTEM
+
CONVERSATION_STATE
+
RECENT_HISTORY
+
MEMORY
+
RAG_EVIDENCE
+
WEB_EVIDENCE
+
TOOL_RESULTS
+
USER_INPUT
+
OUTPUT_RESERVE
```

The budget must be measured with the tokenizer of the active model/runtime.

Initial policy for Qwen3.6:

| Workload | Target working context |
| --- | ---: |
| Short/simple chat | 8K–16K |
| Normal corporate chat | 24K–32K |
| Complex reasoning | 32K–64K |
| Large document / multi-source task | 64K–128K |
| Exceptional whole-context case | up to 262K |

These are operating targets, not hard limits.

The system must reserve output capacity and must never assume that the full 262144 tokens are available for input.

## Context selection

The Context Manager should rank candidate context by:

1. mandatory policy priority;
2. active task relevance;
3. explicit user constraints;
4. confirmed decisions;
5. semantic relevance;
6. source authority;
7. freshness;
8. lifecycle validity;
9. recency;
10. token cost.

Retrieval score alone is not sufficient to determine importance or truth.

## Summarization

Older conversation segments may be summarized when the active working context approaches its budget.

Summaries must preserve:

- decisions;
- constraints;
- unresolved questions;
- important facts;
- task state;
- references to source messages;
- relevant entities;
- contradictions.

A summary must never erase the underlying persistent history.

## Memory extraction

Memory extraction runs as a post-processing step or controlled asynchronous task.

The extractor may propose:

- facts;
- decisions;
- preferences;
- constraints;
- tasks;
- events;
- entities;
- summaries;
- milestones.

High-impact or ambiguous memories may require validation before becoming ACTIVE.

Memory extraction must not modify corporate source-of-truth records without an explicit controlled workflow.

## Conflict handling

Memory conflicts follow the same general principle as Corporate AI evidence conflicts.

Example:

Memory A:
```
Open WebUI is the authoritative corporate knowledge store.
```

Memory B:
```
Corporate AI remains authoritative and Open WebUI is the user workspace.
```

The system must identify the conflict and prefer an authoritative validated project decision only when such authority is available.

It must not resolve conflicts solely through embedding similarity, recency or model confidence.

## Tool and web result handling

Large tool outputs must not be appended indefinitely to the chat context.

The flow should be:

```
Tool call
    ↓
Tool result
    ↓
Result processor
    ├── raw result → persistent artifact
    ├── structured result → persistent record
    ├── relevant subset → active context
    └── provenance → context metadata
```

The same rule applies to Web Search and Web Fetch.

## Observability

Every LLM context build should produce a context-run record containing, where available:

- context_run_id
- conversation_id
- model
- configured context budget
- actual input tokens
- output tokens
- system tokens
- state tokens
- history tokens
- memory tokens
- RAG tokens
- web tokens
- tool tokens
- selected message IDs
- selected memory IDs
- selected source IDs
- truncated/excluded item counts
- final context composition

This telemetry is required to diagnose context quality, latency and resource consumption.

Private model chain-of-thought must not be persisted as conversation memory or exposed through telemetry.

## Initial persistence model

Recommended PostgreSQL entities:

- conversations
- conversation_messages
- conversation_state
- conversation_summaries
- conversation_memories
- conversation_milestones
- conversation_entities
- conversation_context_runs
- conversation_context_items
- conversation_artifacts

Qdrant may maintain a derived collection/index for semantic retrieval of memories and conversation segments.

Redis is optional for hot session state and must not become the authoritative store.

## Security and isolation

Conversation content is untrusted user data.

Memory, history, RAG evidence, Web content and tool results must not override:

- system instructions;
- security policy;
- access controls;
- authorization;
- tool policy.

Memory retrieval must respect conversation/user/tenant/project scope.

Cross-conversation memory leakage is a security defect.

## V1 acceptance scope

V1 should implement:

- persistent conversation history;
- conversation state;
- recent-history selection;
- conversation summarization;
- structured memory extraction;
- memory retrieval;
- milestones;
- adaptive context budgeting;
- model-aware token counting;
- deterministic context assembly;
- context telemetry;
- memory provenance;
- memory lifecycle;
- basic memory conflict detection;
- strict separation of conversation memory from Corporate Knowledge evidence.

V1 does not require a dedicated Knowledge Graph for memory.

## Relationship with AI Orchestrator

The AI Orchestrator consumes Conversation & Context Management as a context service.

The Orchestrator decides the task and required capabilities.

The Context Manager decides which conversation state, history and memory are relevant and how they fit into the context budget.

Knowledge Engine remains responsible for Corporate Knowledge retrieval and evidence semantics.

Web Search remains responsible for controlled external retrieval.

Tool Gateway remains responsible for tool execution policy.

No module should duplicate another module's source-of-truth responsibilities.
