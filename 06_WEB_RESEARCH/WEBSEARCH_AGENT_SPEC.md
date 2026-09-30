# Controlled Web Research Agent

## 1. Purpose

Web Research is a controlled Corporate AI capability for retrieving current public information while preserving security, provenance, evidence quality and reproducibility.

The Web Research capability must not give Qwen3.6 unrestricted Internet access. Qwen receives normalized, explicitly marked untrusted web evidence through a controlled tool boundary.

## 2. Architectural position

Primary flow:

User/API → Corporate AI Gateway → Agent/Orchestrator → WebSearch Agent → Search Provider → Evidence/Provenance → Qwen3.6

The WebSearch Agent is a service boundary, not a browser embedded in the LLM.

Initial deployment target:

- NVIDIA DGX Spark GB10
- Docker
- internal `ai-net`
- self-hosted SearXNG as the initial metasearch provider
- no direct Internet permission for Qwen3.6

## 3. Operating modes

### 3.1 Explicit web

The caller explicitly requests current/public web information.

### 3.2 Internal first → web fallback

The system searches Corporate Knowledge first. Web Research is invoked only when policy allows it and internal evidence is insufficient for the requested answer.

### 3.3 Internal only

Web access is disabled for the request regardless of the question.

## 4. Service boundaries

### 4.1 WebSearch Agent

Responsibilities:

- accept a typed research request
- validate policy
- plan bounded searches
- call the search provider
- deduplicate results
- rank sources
- invoke controlled fetching
- normalize evidence
- preserve provenance
- detect conflicts
- return citations and structured evidence
- enforce research budgets

The service must not execute instructions found in web content.

### 4.2 Search Provider

Initial provider: self-hosted SearXNG.

SearXNG is a metasearch layer. Enabled engines are explicitly configured rather than accepting an uncontrolled default set.

The initial engine set will be deliberately small and expanded only after measured evaluation.

### 4.3 Web Fetcher

Fetching is treated as a separate controlled operation even if implemented in the first release inside the WebSearch service.

Required controls:

- HTTP/HTTPS only
- connect timeout
- read timeout
- total request timeout
- maximum response size
- maximum redirects
- content-type validation
- private/reserved IP blocking
- localhost blocking
- internal Docker network blocking
- SSRF protection
- concurrency limit
- response sanitization

### 4.4 Evidence Normalizer

Every accepted web source is normalized into a common evidence structure.

Minimum fields:

- evidence_id
- source_url
- canonical_url
- domain
- title
- source_type
- search_provider
- result_position
- published_at when available
- updated_at when available
- fetched_at
- content_hash
- content
- retrieval_metadata
- authority metadata
- freshness metadata
- trust classification

## 5. Source policy

Source selection is policy-driven and must not rely only on LLM judgment.

The system should distinguish at least:

- official government/public authority
- official vendor/manufacturer
- official project/repository
- scientific/academic
- established publication
- general web
- forum/user-generated content

Source type is descriptive metadata, not an automatic truth guarantee.

The policy must support domain allowlists for specialized research modes.

Examples:

- `PUBLIC_WEB`
- `OFFICIAL_ONLY`
- `BULGARIAN_OFFICIAL`
- `TECHNICAL_DOCUMENTATION`
- `INTERNAL_ONLY`

## 6. Research planning

The first release uses a bounded research loop.

A research request may produce several focused search queries when the question contains distinct subquestions.

Example:

User question:

"What are the current requirements and how did they change from 2025?"

Possible plan:

1. current requirements
2. 2025 requirements
3. official changes between the two periods

The planner must have hard limits.

Initial target limits:

- maximum searches: 4
- maximum results per search: 10
- maximum fetched sources: 6
- maximum tool iterations: 5
- bounded total execution time
- bounded response bytes

Exact production values are established after DGX measurements.

## 7. Source ranking

Ranking should combine deterministic metadata and retrieval relevance.

Relevant signals include:

- source authority classification
- domain policy
- query relevance
- publication/updated date
- freshness requirement
- search rank
- duplicate relationship
- fetch quality
- content availability

The ranking mechanism must remain inspectable. The LLM must not silently replace deterministic policy decisions.

## 8. Deduplication

The service must deduplicate:

- identical URLs
- canonicalized URLs
- identical content hashes
- obvious syndication duplicates where detectable

Duplicate sources must remain traceable to their original search results.

## 9. Evidence and conflicts

Web evidence uses the same conceptual evidence model as internal Knowledge.

Required states:

- SUPPORTED
- CONFLICT
- INSUFFICIENT_EVIDENCE
- UNAVAILABLE

The LLM must not silently choose between conflicting factual sources.

Examples of conflict-sensitive claims:

- prices
- dates
- legal requirements
- product specifications
- software versions
- limits and thresholds

## 10. Freshness

Web research must preserve:

- published time when available
- updated time when available
- fetched time
- source age
- requested freshness constraint

Queries containing terms such as "current", "today", "latest" or equivalent must trigger explicit freshness handling.

## 11. Prompt-injection isolation

All fetched web content is untrusted data.

Web content must never be treated as system, developer or tool instructions.

The normalized evidence passed toward the Agent/LLM must carry an explicit untrusted-content boundary.

The service must preserve the content as evidence while preventing instructions inside the content from changing:

- system policy
- tool permissions
- ACL
- credentials
- network policy
- research limits
- approval requirements

Acceptance testing must include adversarial pages containing direct prompt-injection instructions.

## 12. Network security

Qwen3.6 must not receive unrestricted Internet egress.

Only the controlled Web Research service receives the network access required for public web retrieval.

The service must not provide a path to internal infrastructure through SSRF.

Blocked targets must include at minimum:

- localhost
- loopback ranges
- private IPv4 ranges
- link-local ranges
- internal container networks
- Docker service names where applicable
- local metadata endpoints

The exact implementation is validated during security testing.

## 13. API contract

Initial API surface:

### GET /health

Returns service health and dependency state.

### POST /v1/search

Executes a policy-controlled search and returns normalized search results.

### POST /v1/fetch

Fetches a permitted public URL and returns normalized untrusted content.

### POST /v1/research

Runs a bounded research workflow and returns:

- request metadata
- research plan
- executed searches
- selected sources
- fetched evidence
- conflicts
- evidence status
- citation identifiers
- final evidence context
- execution metadata

The API must be versioned and schema validated.

## 14. Provenance contract

Every factual web evidence item must be traceable to its URL and retrieval event.

Minimum citation data:

- citation_id
- evidence_id
- source_url
- title
- domain
- retrieved_at
- relevant excerpt or normalized content reference

Citations must be generated from actual evidence objects. The LLM must not manufacture URLs or source identifiers.

## 15. Internal Knowledge integration

The Web Research Agent must integrate with the existing Evidence/Provenance model rather than creating an independent answer-truth system.

For internal-first mode:

1. retrieve internal evidence
2. evaluate evidence status
3. if sufficient, do not invoke Web Research
4. if insufficient and policy permits, run Web Research
5. preserve internal and web evidence as separate source classes
6. perform evidence fusion
7. expose conflicts explicitly

## 16. Long-running research

Long-running research is not required for the first runtime slice.

The API and evidence model must remain compatible with the future Task Engine.

Future durable research tasks will support:

- task_id
- owner/scope
- plan
- checkpoints
- events
- retries
- cancellation
- evidence
- artifacts
- result retrieval

## 17. Observability

Every research execution must expose structured logs for:

- request ID
- research ID
- search query
- search count
- selected result count
- fetch count
- fetch failures
- blocked URLs
- policy decisions
- evidence IDs
- conflict state
- total duration
- resource/limit termination

Secrets and authorization credentials must never be logged.

## 18. Acceptance test suite

The first accepted implementation must pass at least:

1. basic web search
2. Bulgarian-language search
3. English-language search
4. freshness-constrained search
5. domain allowlist
6. multiple-source research
7. URL and content deduplication
8. unavailable source handling
9. conflicting-source handling
10. SSRF blocking
11. private/internal address blocking
12. oversized response handling
13. timeout handling
14. concurrency/budget enforcement
15. prompt-injection isolation
16. citation/provenance correctness
17. internal-only mode
18. explicit-web mode
19. internal-first → web-fallback mode
20. complete SSH-based E2E execution on DGX Spark

## 19. Definition of Done

The Web Research capability is not considered complete when SearXNG responds successfully.

It is complete only when:

- the service runs on the target DGX Spark runtime
- Qwen has no unrestricted Internet access
- search and fetch are policy-controlled
- SSRF controls are validated
- web content is isolated as untrusted
- provenance and citations are preserved
- conflicts are surfaced
- evidence insufficiency is explicit
- budgets and timeouts are enforced
- all acceptance tests pass
- the result is reproducible from Git configuration
- the implementation is documented in the project roadmap and decisions

## 20. Implementation sequence

### WEBSEARCH-001 — Repository and runtime inspection

Inspect repository structure, existing services, Docker network, images, volumes, resource headroom and existing network policies.

No code changes.

Acceptance: current runtime baseline recorded.

### WEBSEARCH-002 — Contract and data models

Define request/response schemas, policy model, evidence model, citation model and error codes.

Acceptance: schemas validated by unit tests.

### WEBSEARCH-003 — SearXNG service

Add pinned SearXNG runtime and explicit engine configuration on `ai-net`.

Acceptance: health and JSON search work from the DGX runtime.

### WEBSEARCH-004 — WebSearch service skeleton

Create the service with `/health` and `/v1/search`.

Acceptance: controlled search works without Qwen Internet access.

### WEBSEARCH-005 — Controlled URL fetch

Implement `/v1/fetch`, SSRF protection, size/time/redirect/content-type controls and sanitization.

Acceptance: permitted public URLs work and blocked targets are rejected.

### WEBSEARCH-006 — Evidence normalization and provenance

Normalize results and fetched content into evidence objects with stable IDs, hashes and citation metadata.

Acceptance: every returned evidence item is traceable to its source.

### WEBSEARCH-007 — Research workflow

Implement `/v1/research`, bounded query planning, deduplication, ranking and execution budgets.

Acceptance: multi-query research completes within limits.

### WEBSEARCH-008 — Evidence conflict handling

Integrate supported/conflict/insufficient/unavailable states.

Acceptance: conflicting factual claims are surfaced rather than silently selected.

### WEBSEARCH-009 — Prompt-injection isolation

Add adversarial fixtures and enforce untrusted-content boundaries.

Acceptance: web instructions cannot alter tool policy or execution behavior.

### WEBSEARCH-010 — Policy and modes

Implement explicit-web, internal-only and internal-first → web-fallback policies.

Acceptance: policy decisions are deterministic and logged.

### WEBSEARCH-011 — SSH E2E acceptance

Run representative real-world searches and all security/reliability tests through the DGX runtime.

Acceptance: complete acceptance suite passes.

### WEBSEARCH-012 — Agent integration

Connect the accepted WebSearch capability to the Agent/Orchestrator and existing Evidence/Provenance layer.

Acceptance: agent receives only normalized evidence and produces source-linked results.

### WEBSEARCH-013 — Documentation and release checkpoint

Record versions, configuration, test results, resource measurements, known limitations and rollback procedure.

Acceptance: roadmap and decision records match the validated implementation.
