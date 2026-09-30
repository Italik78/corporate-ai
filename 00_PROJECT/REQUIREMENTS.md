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
- model registry and reproducible runtime configuration
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

## Models

Production models must have versioned registry records, local artifacts, reproducible runtime configuration, health checks, validation results and rollback targets.

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

## Controlled Web Research

The Web Research capability must satisfy the following requirements:

- Qwen3.6 must not have unrestricted Internet access.
- Web access must pass through a controlled WebSearch capability.
- The initial search provider must be self-hosted SearXNG with an explicit engine configuration.
- Search and URL fetching must be policy-controlled operations.
- URL fetching must enforce SSRF protection and block localhost, private/reserved addresses and internal service networks.
- URL fetching must enforce timeout, response-size, redirect, content-type and concurrency limits.
- Web content must be treated as untrusted data and must not modify system/developer policy, tool permissions, ACL, credentials or research limits.
- Web evidence must preserve URL, canonical URL, domain, timestamps, content hash and retrieval provenance.
- Web evidence must have stable evidence and citation identifiers.
- Web Research must distinguish SUPPORTED, CONFLICT, INSUFFICIENT_EVIDENCE and UNAVAILABLE states.
- Conflicting factual sources must not be silently resolved by the LLM.
- Research execution must have hard limits for searches, results, fetches, iterations, execution time and response size.
- The service must support explicit-web, internal-only and internal-first → web-fallback operating modes.
- Domain allowlists must be supported for specialized research policies.
- The first implementation must be validated through SSH on the DGX Spark before Open WebUI integration.
- Security acceptance must include SSRF and prompt-injection adversarial tests.
- Complete source provenance and citation correctness must be verified in E2E tests.
