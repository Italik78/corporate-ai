# GATEWAY AND AGENT

## Responsibility boundary

### Corporate AI Gateway

The Gateway is the controlled entry point for:
- Open WebUI
- API clients
- ERP/CRM
- n8n/webhooks
- schedulers
- internal applications

Responsibilities:
- authentication/identity
- authorization and ACL
- session handling
- policy enforcement
- request validation
- rate/concurrency limits
- audit
- task submission
- routing to the Agent/Orchestrator

The Gateway does not become the LLM itself.

### AI Agent / Orchestrator

The Agent coordinates multi-step work.

Responsibilities:
- intent/task classification
- planning
- context assembly
- memory retrieval/write decisions
- skill selection
- prompt selection
- knowledge retrieval
- Web Research
- tool selection
- task checkpoints
- evidence evaluation
- final-answer validation
- human approval requests

## Request lifecycle

```
Request
  ↓
Identity + ACL
  ↓
Intent / task classification
  ↓
Load relevant conversation context
  ↓
Load relevant memory
  ↓
Select skill(s)
  ↓
Select/version prompts
  ↓
Build plan
  ↓
Execute Knowledge / Web / Vision / Tools
  ↓
Collect evidence and provenance
  ↓
Validate result
  ↓
Write approved durable memory/task state
  ↓
Generate final response
```

## Context assembly

The Agent never sends the entire available history by default.

Context is assembled from:
1. system/policy instructions
2. current user request
3. relevant recent turns
4. relevant conversation summary
5. relevant project memory
6. relevant task state
7. selected knowledge evidence
8. selected Web evidence
9. selected tool results
10. skill/prompt instructions

A Context Budget Manager must enforce model context limits.

## Memory rules

Memory is retrieved by relevance, scope and permission.

The Agent must distinguish:
- conversation memory
- project memory
- task state
- corporate knowledge
- user preferences

A statement from a conversation does not automatically become corporate knowledge.

A document does not automatically become memory.

Memory writes require an explicit policy and provenance.

## Skill selection

Skills are selected by:
- explicit user request
- task type
- capability requirements
- permissions
- skill availability
- dependency health

Skills cannot bypass Gateway policy.

## Prompt selection

Prompts are selected by:
- task
- skill
- model
- language
- environment
- version policy

Production prompts are immutable by ordinary tool execution and are changed through the Prompt Registry lifecycle.

## Tool execution

```
Agent
 ↓
Tool selection
 ↓
Policy check
 ↓
Schema validation
 ↓
ACL/approval check
 ↓
Execution
 ↓
Result validation
 ↓
Provenance/audit
 ↓
Agent
```

High-impact actions require explicit human approval unless an approved policy says otherwise.

## Long-running tasks

For work that may exceed a normal request:
- create a durable task
- persist plan and state
- execute in worker
- checkpoint progress
- persist evidence/artifacts
- allow status/cancel/retry
- return a final result when complete

Chat remains the interactive interface; Task API handles durable execution.

## Failure behavior

The Agent must fail closed for:
- unauthorized data
- unavailable required evidence
- invalid tool arguments
- policy violations
- unsafe document instructions
- missing required dependencies

It must expose controlled errors rather than fabricate a result.
