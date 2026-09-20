# OPEN WEBUI INTEGRATION & WEB SEARCH ARCHITECTURE v1

## Purpose

Define how Open WebUI participates in Corporate AI without becoming a second source of truth for documents, embeddings, retrieval policy or business logic.

The design must preserve:

- Document Ingestion as the authoritative ingestion pipeline.
- PostgreSQL as document metadata/version source of truth.
- Object Storage as the source of original files.
- Qdrant as the retrieval index.
- Knowledge Engine as the evidence/RAG boundary.
- Gateway/Agent as the controlled orchestration and tool-policy layer.
- Open WebUI as the primary interaction and presentation layer.

The design also introduces controlled Web Search without giving the LLM unrestricted Internet access.

## Findings from Open WebUI capabilities

The current Open WebUI platform provides several relevant extension points:

1. External Knowledge Sources can connect Open WebUI directly to Qdrant, Milvus or pgvector. Open WebUI can map content, title, source, URL, document ID, page, metadata and score from the external vector store.
2. Knowledge Bases support focused retrieval and full-context modes and expose native knowledge tools such as semantic search, exact/regex search and paginated file reading.
3. Native function calling can expose Web Search and URL fetching as tools.
4. Open WebUI supports external OpenAPI and MCP tool servers.
5. Filter Functions can intercept requests. The documented `file_handler` mechanism can replace the built-in file RAG path with controlled custom retrieval.
6. Web Search supports multiple providers including DuckDuckGo, SearXNG, Brave, Tavily and others. Web content can also be fetched after search.
7. Agentic Web Search allows the model to decide when to search and when to follow a result URL.

These capabilities are integration mechanisms, not reasons to move Corporate AI business logic into Open WebUI.

## Architectural decision

Open WebUI remains the user-facing interaction layer.

Corporate AI owns:

- document ingestion;
- normalization;
- versioning;
- lifecycle;
- access control;
- embeddings;
- retrieval policy;
- evidence evaluation;
- provenance;
- Agent planning;
- tool authorization;
- Web Search policy;
- generated artifact provenance.

Open WebUI may provide UI-level access to these capabilities through controlled integrations.

## Target architecture

```
User
  |
  v
Open WebUI
  |
  v
Corporate AI Gateway
  |
  +--------------------+
  |                    |
  v                    v
Agent / Orchestrator   Knowledge Engine
  |                    |
  |                    +--> Qdrant
  |                         ^
  |                         |
  +--> Document Tools       |
  |                         |
  +--> Office Tools         |
  |                         |
  +--> Web Search Gateway --+
  |
  v
Qwen3.6

Document path:
Open WebUI upload
  -> controlled file integration
  -> Document Ingestion
  -> PostgreSQL metadata/version registry
  -> Object Storage (production)
  -> extraction/OCR/Vision
  -> normalized blocks
  -> structure-aware chunks
  -> Qwen3-Embedding-4B
  -> Qdrant
  -> Knowledge Engine
  -> Agent/Gateway
  -> grounded answer

Web path:
User question
  -> Gateway/Agent
  -> Web Search policy
  -> controlled search provider
  -> result normalization
  -> URL fetch when required
  -> source/provenance records
  -> Agent evidence evaluation
  -> answer with web citations

The LLM never receives unrestricted Internet/network access.
```

## Open WebUI document handling

### Problem observed

The standard Open WebUI file upload currently processes XLSX internally:

```
Open WebUI upload
  -> Open WebUI extraction
  -> Open WebUI embedding
  -> file-* vector collection
```

This bypasses Corporate AI Document Ingestion, PostgreSQL metadata/versioning and the `corporate_knowledge` collection.

Therefore the standard Open WebUI RAG path must not become the production document source of truth.

### Preferred integration strategy

Evaluate and implement the following in order:

1. **Controlled file integration through Open WebUI Filter/file_handler** where it can preserve the existing upload UX while delegating retrieval/processing to Corporate AI.
2. **External Knowledge Source backed by Qdrant** for retrieval from `corporate_knowledge`, provided the Open WebUI deployment can use the same Qwen3-Embedding-4B model and 2560 dimensions for query vectors.
3. **OpenAPI/MCP tools** for explicit document operations such as search, inspect, compare and analyze.
4. Keep native Open WebUI file RAG disabled or unused for Corporate AI knowledge whenever it would create a parallel vector/index path.

The external Qdrant integration is currently documented as experimental, so it must be validated on the installed Open WebUI version before being treated as a production dependency.

## Embedding rule

All vectors in `corporate_knowledge` are produced with Qwen3-Embedding-4B, 2560 dimensions.

Any Open WebUI external Qdrant retrieval path that creates query embeddings must use the same embedding model and dimensionality.

Do not use:

- `sentence-transformers/all-MiniLM-L6-v2`
- Open WebUI's auxiliary embedding model
- another embedding model with different dimensions

for production retrieval against `corporate_knowledge`.

If Open WebUI cannot safely use the production embedding service, retrieval should go through Knowledge Engine instead of bypassing it.

## Knowledge Base strategy

Open WebUI Knowledge UI can remain available for user-facing organization of knowledge.

However, a Corporate AI Knowledge Base must represent or reference the authoritative Corporate AI knowledge rather than create a second independent copy.

Recommended logical scopes:

- Corporate Policies
- Procedures / Standards
- Projects
- Contracts
- Procurement
- Temporary Task Documents
- Generated Artifacts

The authoritative metadata, lifecycle and access decisions remain outside Open WebUI.

Focused retrieval is the normal mode.

Full Context is allowed only for small bounded documents or explicitly planned tasks.

Whole-document analysis remains an Agent workflow and is not implemented by blindly enabling Full Context.

## Web Search architecture

Web Search is required because internal corporate knowledge is not sufficient for:

- current public information;
- current regulations and public guidance;
- vendor/product research;
- public technical documentation;
- external market research;
- verification of facts outside the corporate corpus.

Web Search must be treated as a separate evidence source, not mixed silently with internal corporate evidence.

### Security boundary

The primary LLM must not receive unrestricted Internet access.

Instead:

```
LLM
  |
  | tool call
  v
Web Search Gateway / controlled provider
  |
  +--> Search API
  +--> URL fetcher
  +--> domain/egress policy
  +--> timeout/concurrency limits
  +--> content-size limits
  +--> provenance
  v
normalized web evidence
  |
  v
Agent evidence evaluation
  |
  v
Qwen3.6
```

The search service may have Internet egress; the model container does not.

### Search modes

#### Mode 1 — Explicit web search

User asks for current/public information or explicitly requests web research.

Agent calls `search_web`.

#### Mode 2 — Internal-first, web fallback

For mixed questions:

1. search authorized internal knowledge;
2. if evidence is insufficient and policy allows, search the public web;
3. keep internal and external evidence distinct;
4. state which claims come from which source class.

#### Mode 3 — Internal-only

For confidential corporate tasks, the Agent can be configured to prohibit web access.

Examples:

- internal policy interpretation;
- contract review;
- employee/private information;
- confidential project documents.

#### Mode 4 — Research workflow

For research tasks:

1. formulate search queries;
2. search multiple sources;
3. fetch selected pages;
4. deduplicate;
5. preserve URLs and retrieval timestamps;
6. evaluate source quality;
7. synthesize with explicit citations.

## Web Search provider strategy

Preferred deployment order:

### A. Self-hosted SearXNG

Candidate default for the controlled architecture.

Advantages:

- self-hosted;
- no provider API key in the LLM;
- can aggregate multiple upstream search engines;
- central place for outbound search policy.

It still requires Internet egress from the search service.

### B. Hosted search provider

Use when search quality or reliability justifies it.

Candidate providers supported by Open WebUI include Brave, Tavily, Kagi, Serper, SerpAPI, Mojeek, DuckDuckGo and others.

Credentials must stay server-side and never enter model context.

### C. Open WebUI native Web Search

Useful as a UI capability and validation path.

For the final Corporate AI architecture, prefer routing web research through the same controlled policy/provenance layer as other tools if possible.

## Web evidence model

A web result should be normalized approximately as:

```
WebEvidence
  query
  result_id
  title
  url
  domain
  snippet
  fetched_at
  published_at (if available)
  content
  content_hash
  retrieval_method
  source_rank
  confidence
  access_scope = PUBLIC
```

The Agent must preserve the relationship:

```
answer claim
  -> evidence
      -> URL
      -> fetched content
      -> retrieval timestamp
```

Internal document evidence and web evidence must not be assigned the same provenance identity.

## Web security and resource policy

Required controls:

- allowed/blocked domains;
- HTTP/HTTPS policy;
- request timeout;
- maximum response size;
- maximum pages per research task;
- maximum concurrent fetches;
- redirect limits;
- content-type restrictions;
- HTML/script sanitization;
- prompt-injection isolation;
- no automatic tool authorization from web content;
- no secrets in outbound requests;
- audit logging;
- retryable versus terminal network errors.

Web pages are untrusted data exactly like uploaded documents.

Web content cannot:

- change system instructions;
- authorize a tool;
- alter access controls;
- request secrets;
- override Agent policy.

## Citations

Corporate evidence and web evidence use separate citation namespaces.

Example:

```
[Internal 1]
[Internal 2]

[Web 1]
[Web 2]
```

The final answer should make the source class visible.

For time-sensitive web claims, the retrieval date/time must be retained in provenance.

## Open WebUI tools

Open WebUI's native tools are useful for:

- Web Search;
- URL fetching;
- Knowledge browsing;
- user-facing file interaction.

Corporate tools should be exposed through controlled OpenAPI/MCP servers where they have business or security significance.

Examples:

- `search_corporate_knowledge`
- `analyze_document`
- `compare_documents`
- `create_word`
- `create_excel`
- `create_powerpoint`
- `create_pdf`
- `search_web`
- `fetch_web_page`

Tool execution remains subject to Corporate AI Tool Policy.

## Phase plan

### Phase C1 — Open WebUI integration discovery

- [ ] Confirm installed Open WebUI version and exact enabled capabilities.
- [ ] Validate External Knowledge → Qdrant against `corporate_knowledge`.
- [ ] Determine whether Open WebUI can use Qwen3-Embedding-4B query embeddings directly.
- [ ] Validate metadata mappings and citations.
- [ ] Validate Knowledge Base behavior with external knowledge.
- [ ] Decide whether Filter/file_handler is needed for upload integration.
- [ ] Disable/avoid parallel Open WebUI RAG for Corporate AI production knowledge.

### Phase C2 — Controlled document upload

- [ ] Preserve Open WebUI upload UX.
- [ ] Route uploaded files into Document Ingestion.
- [ ] Register metadata/version before indexing.
- [ ] Store originals outside Qdrant.
- [ ] Preserve source/provenance.
- [ ] Validate DOCX/XLSX/PPTX/CSV end-to-end.
- [ ] Add PDF/OCR/Vision path.

### Phase C3 — Knowledge integration

- [ ] Expose Corporate Knowledge through Knowledge Engine or validated external Qdrant integration.
- [ ] Enforce version/lifecycle/project/access filters.
- [ ] Preserve evidence claims and citations.
- [ ] Validate Knowledge UI with current and superseded versions.

### Phase C4 — Web Search foundation

- [ ] Decide between self-hosted SearXNG and a hosted provider.
- [ ] Deploy search service behind controlled egress.
- [ ] Implement normalized web evidence.
- [ ] Implement URL fetching with limits.
- [ ] Add web-source citations and timestamps.
- [ ] Add prompt-injection isolation.
- [ ] Add domain and resource policies.

### Phase C5 — Agent integration

- [ ] Add internal-first/web-fallback routing policy.
- [ ] Add explicit research workflow.
- [ ] Add cross-source evidence evaluation.
- [ ] Keep internal and web evidence separate.
- [ ] Add confirmation for high-impact actions.
- [ ] Add traceability for generated artifacts.

### Phase C6 — Production validation

- [ ] Upload DOCX/XLSX/PPTX/CSV from Open WebUI.
- [ ] Verify PostgreSQL registry.
- [ ] Verify Qdrant payload and version filters.
- [ ] Ask grounded internal questions.
- [ ] Ask explicit web questions.
- [ ] Ask mixed internal + web questions.
- [ ] Verify citations and provenance.
- [ ] Test blocked-domain and prompt-injection cases.
- [ ] Test search timeout/resource exhaustion.
- [ ] Test offline/internal-only mode.

## Acceptance criteria

The integration is accepted only when:

1. Open WebUI upload does not silently create a second production knowledge index.
2. A document uploaded from the UI reaches Corporate AI Document Ingestion.
3. Metadata/version/lifecycle is registered in PostgreSQL.
4. Original content is stored outside Qdrant.
5. Normalized chunks reach `corporate_knowledge`.
6. Retrieval uses the correct embedding model.
7. Version/access/project filters remain effective.
8. Answers preserve provenance.
9. Web Search works through controlled egress.
10. Web evidence is separately identifiable from internal evidence.
11. Web content cannot override system/tool policy.
12. The LLM has no unrestricted network access.
13. All major paths are validated on the DGX runtime.

## Current decision

Do not implement a custom Open WebUI upload workaround yet.

First validate the documented Open WebUI extension points on the installed deployment:

1. External Knowledge → Qdrant.
2. Filter/file_handler.
3. Native Web Search / tool calling.

Then implement the smallest integration that preserves the Corporate AI source-of-truth boundaries.
