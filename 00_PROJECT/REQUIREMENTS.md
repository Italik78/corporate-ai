# REQUIREMENTS

## Functional
- Bulgarian-first corporate assistant
- reasoning and instruction following
- grounded RAG with citations
- explicit uncertainty and refusal when evidence is insufficient
- JSON/tool calling
- long context
- vision
- document understanding
- large-document processing without blindly filling the LLM context
- structure-aware extraction and chunking
- document versioning and document relationships
- project/document scoped retrieval
- whole-document analysis through bounded Agent workflows
- end-to-end provenance from original document to answer/artifact
- document generation
- vector search
- optional knowledge graph
- agent workflows
- web UI and API

## Agentic reasoning
- task understanding before non-trivial execution
- conversation-context awareness
- clarification when required context is missing
- bounded planning and task decomposition
- dynamic selection between Corporate RAG, Web Research and controlled tools
- iterative retrieval when evidence is insufficient
- applicability reasoning across scope, version, authority and effective dates
- semantic conflict detection and resolution workflow
- verification of material claims before final answer
- controlled no-answer when evidence remains insufficient
- separate provenance for corporate, web and tool evidence
- bounded orchestration steps, tool calls and resource usage
- traceability of material decisions and evidence without exposing private chain-of-thought

## Evidence / truth
The assistant must optimize for verifiable answers rather than answering at any cost.

Material claims should retain:
- provenance
- authority
- applicability
- freshness
- version
- scope
- effective dates
- corroboration/contradiction state

Retrieval score alone must not determine truth.

## Web research
- controlled web search boundary
- internal-first/web-fallback mode
- explicit web-search mode
- internal-only mode
- URL fetching with bounded resources
- web provenance with URL and retrieval timestamp
- web content treated as untrusted data
- no unrestricted model Internet access

## Security
- local inference
- untrusted documents
- controlled tools
- tool policy
- validation before high-impact actions
- no uncontrolled model Internet access
- retrieved content cannot override system/tool policy
- bounded resource usage
- auditable tool execution

## Reliability
- health checks
- versioned configuration
- persistent storage where required
- backups
- recovery procedures
- controlled resource exhaustion
- traceability/provenance
- access-aware retrieval
- bounded resource usage for large-document processing
- reproducible deployments


## Conversation / Context Management
- persistent complete conversation history independent of active LLM context;
- compact conversation state for active topic, task, constraints, decisions and open questions;
- structured contextual memory with provenance, confidence and lifecycle;
- persistent conversation milestones for important decisions and events;
- dynamic context selection rather than fixed sliding-window history;
- model-aware token counting and explicit context budget;
- adaptive context targets with 24K–32K as the normal operating range for Qwen3.6 corporate chat;
- bounded expansion up to 64K–128K for complex/large-document tasks and up to the configured 262K capability only for exceptional cases;
- explicit output reserve in every context budget;
- deterministic/policy-controlled context assembly;
- separate provenance for user statements, conversation memory, corporate evidence, web evidence and tool results;
- memory lifecycle and conflict handling;
- context-run telemetry showing selected and excluded context components;
- protection against cross-conversation memory leakage;
- no persistence or exposure of private model chain-of-thought;
- large tool and web results stored as artifacts or structured results rather than indefinitely appended to chat context.
