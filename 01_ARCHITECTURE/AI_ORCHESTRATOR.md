# AI ORCHESTRATOR / MIND CONTRACT

## 1. Purpose

Corporate AI is not defined as a chat interface with retrieval. The target is a grounded corporate AI assistant that can reason over multiple evidence sources, decide what information is required, retrieve it through controlled capabilities, validate the resulting evidence and answer only to the degree justified by the available evidence.

The Orchestrator is the control layer for this behavior.

The core principle is:

> The assistant must optimize for the best verifiable answer, not for producing an answer at any cost.

The Orchestrator does not become a new source of truth. It coordinates authoritative services and keeps their boundaries intact.

## 2. Architectural position

```
User
  |
  v
Open WebUI
  |
  v
Corporate AI Gateway
  |
  v
AI Orchestrator
  |
  +--> Conversation Context
  +--> Intent / Task Understanding
  +--> Clarification
  +--> Planning / Decomposition
  +--> Corporate Knowledge
  +--> Web Research
  +--> Document Analysis
  +--> Controlled Tools
  +--> Evidence / Truth Evaluation
  +--> Verification
  +--> Answer / Artifact
```

The Orchestrator is between the Gateway and specialized capabilities.

The Knowledge Engine remains responsible for retrieval and evidence representation. The Orchestrator is responsible for deciding what to retrieve, when more evidence is required, how different evidence sources relate to the task and whether the final answer is sufficiently supported.

## 3. Responsibilities

The Orchestrator owns:

- task understanding;
- conversation-context interpretation;
- missing-context detection;
- clarification questions;
- task planning and decomposition;
- capability/tool selection;
- retrieval strategy;
- internal-first/web-fallback decisions;
- bounded research workflows;
- document-analysis planning;
- cross-source evidence evaluation;
- applicability reasoning;
- conflict handling;
- verification loops;
- answerability decisions;
- uncertainty communication;
- provenance assembly;
- user confirmation for high-impact actions;
- execution trace and recovery state.

The Orchestrator does not own:

- authoritative document metadata;
- canonical document bytes;
- vector storage;
- model registry;
- access policy definitions;
- tool authorization policy;
- business-system source-of-truth data.

Those remain in their authoritative services.

## 4. Reasoning loop

Every non-trivial task follows a bounded reasoning loop.

```
REQUEST
  |
  v
UNDERSTAND
  |
  +--> sufficient context? -- NO --> CLARIFY
  |
  v
CLASSIFY TASK
  |
  v
PLAN
  |
  v
RETRIEVE / ACT
  |
  v
EVALUATE EVIDENCE
  |
  +--> insufficient --> RETRIEVE MORE / CLARIFY
  |
  +--> conflict ------> RESOLVE APPLICABILITY / RETRIEVE MORE
  |
  v
VERIFY
  |
  +--> failed --------> revise plan / retrieve more
  |
  v
ANSWER / ARTIFACT
  |
  v
TRACE
```

The loop is bounded by explicit step, tool, time, token and resource budgets.

The model must not silently loop forever.

## 5. Task understanding

The Orchestrator must derive a structured task representation before executing a non-trivial workflow.

Minimum conceptual fields:

```
Task
  task_id
  user_request
  normalized_question
  task_type
  required_output
  conversation_context
  required_context
  known_context
  missing_context
  allowed_source_classes
  sensitivity
  requested_freshness
  answer_constraints
  action_intent
```

Task types include at least:

- factual question;
- corporate knowledge question;
- policy/contract interpretation;
- comparison;
- document analysis;
- research;
- calculation;
- current-information lookup;
- multi-source synthesis;
- tool/action request;
- artifact generation.

Classification is a routing aid, not a source of truth.

## 6. Clarification policy

The assistant must ask a clarification question when a missing variable materially changes the answer and the missing value cannot be established safely from authorized sources or conversation context.

Examples:

- contract type;
- service;
- incident severity;
- location;
- applicable date;
- document/version;
- organizational scope;
- requested output format.

The assistant should not ask for information already present in conversation context or authoritative retrieved evidence.

When several missing variables exist, ask the smallest set of questions required to disambiguate the task.

If a useful partial answer is available, it may be returned together with the missing condition.

## 7. Planning and decomposition

The Orchestrator may decompose a task into bounded subtasks.

Example:

```
"Определи приложимия SLA за критичен инцидент"
  |
  +--> identify contract
  +--> identify service
  +--> identify incident/severity
  +--> identify location/support window
  +--> retrieve applicable clauses
  +--> retrieve exceptions
  +--> compare candidate rules
  +--> verify effective date
  +--> produce applicable SLA
```

Subtasks must retain their parent task and provenance.

The model may propose a plan, but execution remains constrained by policy and tool contracts.

## 8. Source classes

Evidence is separated into source classes.

### CORPORATE

- controlled internal documents;
- contracts;
- policies;
- procedures;
- databases;
- internal APIs.

### WEB

- public websites;
- official public documentation;
- public regulatory sources;
- other permitted Internet sources.

### TOOLS

- business APIs;
- databases;
- calculators;
- controlled application services.

The source class must remain visible in provenance.

Corporate and web evidence must not be silently merged into one undifferentiated knowledge pool.

## 9. Truth / Evidence model

A retrieved fact is not automatically an applicable fact.

Every material claim should be evaluated using:

- provenance;
- authority;
- applicability;
- freshness;
- version;
- scope;
- effective date;
- corroboration;
- contradiction;
- context;
- extraction quality.

Conceptual evidence record:

```
Evidence
  evidence_id
  source_class
  source_id
  source_location
  claim
  authority
  applicability
  freshness
  version
  scope
  effective_from
  effective_to
  confidence
  retrieval_time
  content_hash
```

The Evidence Engine remains responsible for mechanical evidence status such as:

- SUPPORTED;
- CONFLICT;
- INSUFFICIENT_EVIDENCE.

The Orchestrator adds task-level applicability reasoning around those results.

## 10. Conflict handling

The assistant must never select a winner solely because one source was retrieved with a higher vector score.

When conflicting evidence exists:

1. identify the exact conflicting claims;
2. determine whether they describe the same semantic metric;
3. compare scope;
4. compare document/version authority;
5. compare effective dates;
6. inspect exceptions and conditions;
7. retrieve additional evidence when justified;
8. ask the user for missing context when applicability remains unresolved;
9. return a conditional answer or no-answer when the conflict cannot be resolved.

Numeric equality of units is not sufficient to establish a conflict.

For example, "response within 1 hour" and "resolution within 4 hours" are different metrics.

## 11. Corporate RAG strategy

For corporate questions, retrieval should use the strongest available combination of:

- semantic retrieval;
- exact/keyword retrieval;
- metadata filtering;
- version/lifecycle filtering;
- access-scope filtering;
- reranking;
- document relationships;
- structured fields where available.

Exact identifiers, contract numbers, dates, clauses and numeric values must not depend on semantic similarity alone.

The Orchestrator may perform iterative retrieval when the first result set does not establish applicability.

## 12. Web research strategy

Web research is a controlled capability, not unrestricted model browsing.

Modes:

### Explicit web

The user requests current/public research.

### Internal-first / web-fallback

1. search authorized corporate knowledge;
2. evaluate evidence;
3. if insufficient and policy permits, search the web;
4. keep provenance separate;
5. synthesize with visible source classes.

### Internal-only

Web access is prohibited for confidential or policy-restricted tasks.

### Research workflow

For broader research:

1. formulate queries;
2. search multiple permitted sources;
3. fetch selected pages;
4. deduplicate;
5. preserve URLs and timestamps;
6. evaluate source authority and applicability;
7. cross-check material claims;
8. synthesize with citations.

Web content is untrusted data. It cannot issue instructions to the Orchestrator.

## 13. Document reasoning

Large documents are not automatically inserted into the model context.

The Orchestrator chooses between:

- bounded retrieval;
- targeted section retrieval;
- page/section iteration;
- table-specific analysis;
- comparison workflow;
- bounded whole-document analysis.

The original document remains outside Qdrant.

Document version and lifecycle metadata must participate in applicability decisions.

## 14. SLA and conditional-rule reasoning

SLA is the first domain used to validate general reasoning.

An SLA claim should be represented conceptually as:

```
SLARule
  contract
  service
  service_type
  incident_type
  severity
  location
  distance
  support_window
  business_hours
  calendar
  response_target
  resolution_target
  escalation_target
  effective_from
  effective_to
  exceptions
  source_document
  source_clause
  authority
```

The system must not hard-code SLA values into the Orchestrator.

The domain model is an example of conditional evidence reasoning and should later generalize to other corporate rules.

## 15. Verification loop

Before finalizing a material answer, the Orchestrator asks:

- Did I answer the exact question?
- Is each material claim supported?
- Is the evidence applicable to this task?
- Did I accidentally combine different metrics?
- Are there conflicting sources?
- Did a newer or more authoritative version supersede the evidence?
- Is web evidence being presented as internal evidence?
- Did I rely on an untrusted instruction from retrieved content?
- Does the answer need a clarification?
- Can the result be independently checked from the cited evidence?

If verification fails, the task returns to retrieval/planning within its budget.

## 16. Answer contract

A verified answer should preserve:

- answer;
- answer status;
- evidence status;
- source class;
- citations/provenance;
- relevant conditions;
- uncertainty;
- unresolved conflicts;
- clarification requirements when applicable.

The assistant must be comfortable producing:

- a direct answer;
- a conditional answer;
- a partial answer;
- a clarification question;
- a controlled no-answer.

The assistant must not invent facts, citations, sources, tool results or completed actions.

## 17. Tool execution

The Orchestrator may request a tool, but the Tool Policy remains authoritative.

Before execution:

1. validate tool schema;
2. validate arguments;
3. validate permissions;
4. validate resource limits;
5. determine side effects;
6. require user confirmation where policy requires it;
7. execute;
8. validate the result;
9. record provenance and audit information.

Retrieved documents and web pages cannot authorize tools.

## 18. Security model

All retrieved content is untrusted.

This includes:

- PDFs;
- DOCX/XLSX/PPTX;
- OCR output;
- Qdrant chunks;
- web pages;
- search snippets;
- external API content.

Untrusted content must never:

- override system instructions;
- modify tool policy;
- grant permissions;
- request secrets;
- alter access scope;
- cause an unauthorized external action.

The model remains inside the controlled Gateway/tool boundary.

## 19. Resource budgets

Every task has bounded budgets for:

- maximum orchestration steps;
- maximum tool calls;
- maximum web searches;
- maximum fetched pages;
- maximum document sections;
- maximum retrieval candidates;
- maximum execution time;
- maximum generated context;
- maximum artifact size.

Budget exhaustion is a controlled terminal state with an explanation.

## 20. Trace and observability

Every material workflow should be traceable through:

```
task
  -> plan
  -> subtask
  -> retrieval/tool call
  -> evidence
  -> validation
  -> final answer
```

The trace must allow reconstruction of:

- what was requested;
- which sources were consulted;
- which tools ran;
- which evidence supported the answer;
- what conflicts were found;
- why a clarification or no-answer was returned.

Secrets and protected content must not be exposed in logs.

## 21. Recovery

Errors are classified as:

- transient retrieval/tool failure;
- permanent capability failure;
- insufficient evidence;
- unresolved conflict;
- authorization failure;
- resource-budget exhaustion;
- malformed/unsafe input.

The Orchestrator may retry only within bounded policy.

A failed external source must not be silently represented as evidence.

## 22. Implementation boundary

The first implementation should not replace the existing services.

Reuse:

- Corporate AI Gateway;
- Knowledge Engine;
- Qdrant;
- PostgreSQL metadata/version registry;
- Document Ingestion;
- controlled Web Search;
- Tool Policy;
- Qwen3.6.

Add the Orchestrator as the missing coordination layer.

The first production milestone is a bounded orchestration loop with:

1. task understanding;
2. clarification;
3. internal retrieval;
4. controlled web fallback;
5. evidence evaluation;
6. verification;
7. grounded answer;
8. trace.

SLA applicability is the first acceptance scenario.

## 23. Acceptance criteria

The Orchestrator is accepted only when it can demonstrate:

1. It answers a straightforward corporate question from internal evidence with provenance.
2. It asks for missing context when the answer depends on that context.
3. It detects a real semantic conflict without treating unrelated numeric metrics as one conflict.
4. It retrieves additional evidence when the first retrieval set is insufficient.
5. It uses web research only through the controlled boundary.
6. It keeps web and corporate provenance separate.
7. It refuses to treat retrieved instructions as authority.
8. It validates the applicability of document versions and scopes.
9. It verifies material claims before finalizing.
10. It returns a controlled no-answer when evidence remains insufficient.
11. It preserves a trace of the reasoning workflow without exposing private chain-of-thought.
12. It stays within explicit resource and tool budgets.
