# TASK ENGINE

## Purpose

Long-running Corporate AI work must survive beyond a single HTTP/chat request.

The Task Engine provides durable execution for:
- Web Research
- large document processing
- multi-document analysis
- document generation
- batch operations
- scheduled/automated work
- multi-step agent workflows

## Task contract

Each task has:
- task_id
- owner/identity
- project/scope
- task type
- input
- plan
- current state
- checkpoints
- events
- evidence references
- tool calls
- artifacts
- retry count
- approval state
- timestamps
- final result/error

## States

QUEUED → RUNNING → WAITING → COMPLETED

Terminal alternatives:
- FAILED
- CANCELLED

WAITING may mean human approval, external dependency or scheduled continuation.

## Execution

Gateway/API creates the durable task.

Agent creates/updates the plan.

Worker executes individual steps.

Each important step creates a checkpoint so the task can resume after interruption.

## Idempotency

Tasks and tool operations must support idempotency where side effects are possible.

A retry must not create duplicate documents, duplicate payments or duplicate external actions.

## Evidence and artifacts

Task results reference:
- source evidence
- generated documents
- tool outputs
- intermediate artifacts

The final answer is not the only task output.

## Human approval

High-impact actions enter WAITING until explicit approval.

Approval is recorded with:
- identity
- action
- scope
- timestamp
- policy
- result

## API

Target:
- POST /v1/tasks
- GET /v1/tasks/{task_id}
- POST /v1/tasks/{task_id}/cancel
- GET /v1/tasks/{task_id}/result

## Acceptance

A task implementation is accepted only after tests prove:
- persistence across worker restart
- resume from checkpoint
- cancellation
- retry
- idempotency
- approval flow
- artifact persistence
- evidence/provenance
- correct final status
