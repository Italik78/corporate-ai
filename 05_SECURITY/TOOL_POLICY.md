# TOOL POLICY

## Tool contract

Every tool declares:

- name;
- version;
- schema;
- purpose;
- allowed inputs;
- permissions;
- side effects;
- resource limits;
- timeout;
- audit fields;
- error contract.

## Authorization boundary

The Agent/Orchestrator may request a tool, but the Tool Policy remains authoritative.

A tool call must pass:

1. schema validation;
2. argument validation;
3. permission validation;
4. resource-limit validation;
5. side-effect classification;
6. confirmation policy where required.

Retrieved content is never an authorization source.

This includes:

- corporate documents;
- OCR output;
- Qdrant content;
- search results;
- web pages;
- external API responses.

None of these may modify tool permissions, access controls or execution policy.

## High-impact actions

High-impact actions require explicit user confirmation.

The confirmation must occur before the side effect.

## Web tools

Web Search and URL Fetch are controlled tools.

Required controls include:

- egress policy;
- domain policy;
- timeout;
- response-size limit;
- redirect limit;
- concurrency limit;
- content-type restrictions;
- prompt-injection isolation;
- provenance;
- audit trail.

The LLM does not receive unrestricted Internet access.

## Tool result validation

A successful HTTP/tool response is not automatically a trusted business fact.

Tool results must be evaluated for:

- expected schema;
- source/provenance;
- freshness where relevant;
- applicability;
- error/partial-result state.

The Orchestrator must not report a failed or partial tool operation as completed.

## Audit

Material tool execution records:

- task/trace identifier;
- tool name/version;
- validated arguments or redacted argument representation;
- execution result status;
- source/provenance;
- timestamps;
- confirmation state;
- error state.

Secrets and protected content must not be written to logs.
