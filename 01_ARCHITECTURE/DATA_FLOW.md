# DATA FLOW

## Interactive request

User/API → Gateway → identity/ACL/policy → Agent → context assembly → Knowledge/Web/Tools/Vision → Evidence → Qwen3.6 → validation/provenance → response.

## Conversation and memory

Request → recent turns + relevant summaries → memory retrieval by scope/relevance/ACL → Context Budget Manager → LLM.

After response:
- update short-term state
- optionally create durable memory under policy
- persist conversation summary when needed

## Project

Project request → project scope/ACL → project memory + canonical project documents → retrieval → task/answer.

Project memory never replaces canonical repository documents.

## Long-running task

Request → Task API → task record → plan → checkpoints → worker execution → evidence/artifacts → result.

Task can resume after interruption and supports status/cancel/retry.

## Document

File → security intake → classifier/router → extractor/OCR/Vision → normalized structure → metadata/versioning → chunking → embedding → Qdrant → evidence → answer.

## Web Research

Research request → plan → search → fetch → extraction/sanitization → source metadata → claims → cross-check → Evidence Engine → synthesis → citations.

## Tool

Agent → policy → ACL/approval → schema validation → tool → result validation → artifact/provenance/audit → Agent.

## Context principle

Only relevant context is sent to Qwen3.6. Entire repositories, whole documents, unrestricted conversation history and arbitrary tool/Web output are never injected by default.
