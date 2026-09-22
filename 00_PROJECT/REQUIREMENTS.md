# REQUIREMENTS

## Functional

- Bulgarian-first corporate assistant
- reasoning and instruction following
- grounded RAG with citations
- explicit uncertainty and refusal when evidence is insufficient
- JSON/tool calling
- context-budget management and long context
- vision and document understanding
- document generation
- vector search
- optional knowledge graph
- agent workflows
- web UI and API
- controlled Web Research
- short-term conversation memory
- long-term conversation memory
- project memory
- long-running task memory/state
- skill registry and lifecycle
- prompt registry and versioning
- provenance and audit
- human approval for high-impact actions
- task status/cancel/result API
- evaluation and regression testing

## Document formats

PDF, DOCX, DOC, XLSX, PPTX, CSV, TXT, Markdown, PNG, JPEG, TIFF.

## Memory

Memory must be scoped, permission-aware, provenance-aware, relevant before injection, inspectable and deletable, and separated from canonical corporate knowledge.

## Skills and prompts

Skills and prompts must be versioned, testable, auditable, permission/policy aware and reproducible. Production versions are immutable.

## Long-running tasks

Tasks must support durable state, checkpoints, retries, cancellation, artifacts, evidence, progress/status and result retrieval.

## Reliability

- health checks
- versioned configuration
- persistent storage where required
- backups
- recovery procedures
- controlled resource exhaustion
- traceability/provenance
- reproducible deployments
- evaluation suite
- failure/recovery tests

## Security

- local inference
- untrusted documents and Web content
- controlled tools
- tool policy
- ACL
- policy enforcement outside the LLM
- validation before high-impact actions
- no uncontrolled model Internet access
- prompt injection isolation
- secret protection

## Scale-out

The platform must run initially on one DGX Spark and later distribute LLM, worker, application and data services across multiple servers without changing logical contracts.

## Quality

The system must distinguish supported evidence, conflicting evidence and insufficient evidence. It must never manufacture citations or silently select unsupported facts.
