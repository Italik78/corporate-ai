# MEMORY ARCHITECTURE

## Goal

Corporate AI needs memory without turning the LLM context into an uncontrolled permanent database.

Memory is a separate platform capability.

## Memory classes

### 1. Short-term conversation memory

Purpose: keep the current conversation coherent.

Contains:
- recent user/assistant turns
- current task context
- temporary tool results
- temporary decisions

Lifecycle: minutes to session lifetime, with compaction when necessary.

### 2. Long-term conversation memory

Purpose: preserve useful facts from previous conversations.

Examples:
- a previously agreed project decision
- recurring working preference
- an unfinished discussion

It must be:
- scoped to the user/conversation relationship
- explicitly eligible for persistence
- provenance-aware
- editable/deletable

### 3. Project memory

Purpose: maintain durable context for a project.

Examples:
- project goals
- decisions
- constraints
- architecture choices
- milestones
- unresolved questions
- accepted assumptions

Project memory is not a substitute for the project repository. Canonical project documents remain source of truth.

### 4. Long-running task memory

Purpose: resume a task after the original request ends.

Contains:
- task plan
- current step
- checkpoints
- intermediate findings
- evidence references
- tool results
- generated artifacts
- errors/retries
- approval state

### 5. User preference memory

Only where policy and user permission allow it.

Examples:
- preferred output format
- language
- recurring non-sensitive workflow preferences

Sensitive personal information must not be stored merely because it appeared in a conversation.

### 6. Organizational knowledge

Corporate documents, procedures, contracts and policies are not conversational memory.

They belong to the controlled Knowledge Repository with ACL, versions and provenance.

## Storage model

Recommended logical ownership:

```
PostgreSQL
 ├── conversations
 ├── conversation_summaries
 ├── memories
 ├── projects
 ├── project_memory
 ├── tasks
 ├── task_checkpoints
 ├── task_events
 ├── skills
 ├── prompts
 └── audit

Qdrant
 └── optional semantic memory index
```

Semantic indexing must never bypass ACL/scope filtering.

## Memory lifecycle

```
Candidate fact
   ↓
Policy eligibility
   ↓
Scope assignment
   ↓
Provenance
   ↓
Persist
   ↓
Index if useful
   ↓
Retrieve only when relevant
   ↓
Update / supersede / delete
```

## Memory conflict

When memories conflict, the system must not silently choose one.

Use:
- source/provenance
- timestamps
- scope
- explicit supersession
- conflict state

When unresolved, expose the conflict or ask the user.

## Context injection

Only relevant memory is injected into an LLM request.

Priority:
1. current request
2. active task state
3. explicit project context
4. recent conversation
5. relevant durable memory
6. optional semantic memory

The Context Budget Manager controls the final size.

## Deletion

Memory must support:
- user deletion where applicable
- project deletion
- task cleanup/retention
- policy-based retention
- cascade of semantic indexes

Deleting canonical project knowledge is governed by repository lifecycle, not memory deletion.

## Acceptance criteria

Memory is not complete until tests prove:
- short-term continuity
- conversation summarization
- long-term retrieval
- project isolation
- task resume after interruption
- ACL isolation
- memory deletion
- conflict handling
- context-budget enforcement
