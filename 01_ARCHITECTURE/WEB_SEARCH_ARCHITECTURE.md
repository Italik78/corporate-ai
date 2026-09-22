# WEB SEARCH ARCHITECTURE

## Goal

Provide controlled Internet research that produces evidence-based, source-linked results rather than a simple search-result list.

## Principle

Qwen3.6 does not receive unrestricted Internet access.

Web access is a controlled capability:

```
Agent
 ↓
Web Research Service
 ├── query planner
 ├── search provider
 ├── URL fetcher
 ├── extraction
 ├── source metadata
 ├── sanitization
 ├── policy
 └── provenance
 ↓
Web Evidence
 ↓
Evidence Engine
 ↓
Qwen3.6
```

## Research lifecycle

1. Understand the request.
2. Create a research plan.
3. Split the question into verifiable sub-questions.
4. Search for candidate sources.
5. Prefer primary/official sources where appropriate.
6. Fetch controlled source content.
7. Extract relevant claims.
8. Record source, URL, date and retrieval metadata.
9. Cross-check important claims.
10. Detect conflicting claims.
11. Assess evidence sufficiency.
12. Synthesize the result.
13. Cite sources next to claims.
14. State uncertainty and limitations.

## Source classes

Examples:
- primary/official source
- legislation/regulation
- official statistics
- technical documentation
- academic source
- reputable secondary reporting
- commercial source
- community/user-generated source

Source class is metadata, not an automatic guarantee of truth.

## Evidence contract

Each important claim should have:
- claim_id
- claim text
- source_id(s)
- source URL
- source class
- publication date when available
- retrieval timestamp
- supporting excerpt/reference
- evidence status
- confidence/quality metadata
- conflict references

## Conflict handling

If sources disagree:
- retain both claims
- record the disagreement
- evaluate source context/date/scope
- do not silently select a winner
- state the conflict when it materially affects the answer

## Web safety

Fetched pages are untrusted input.

The service must defend against:
- prompt injection
- malicious instructions
- oversized responses
- unsupported content types
- excessive redirects
- SSRF
- unsafe URLs
- credential leakage
- tool invocation hidden in page content

Web content is evidence/data, never system instruction.

## Research output

A research result should separate:
- verified facts supported by sources
- attributed claims
- analysis/inference
- unresolved questions
- conflicts
- limitations

The system must not manufacture citations.

## Resource controls

The service needs:
- domain policy
- URL allow/deny policy where required
- request timeout
- response-size limits
- concurrency limits
- crawl depth limits
- retry policy
- caching policy
- rate limiting
- audit

## Acceptance criteria

Web Research is not complete until benchmark tests cover:
- factual accuracy
- citation correctness
- source provenance
- primary-source handling
- conflicting sources
- insufficient evidence
- prompt injection
- inaccessible/changed pages
- multi-step research
- long-running research tasks
