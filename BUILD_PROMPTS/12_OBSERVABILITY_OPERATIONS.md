# EXECUTION PROMPT — Observability and Operations

You are implementing one component of the **Italik78/corporate-ai** repository.

## Mandatory context

Before changing code, read:
- 00_PROJECT/PROJECT_MASTER.md
- 00_PROJECT/REQUIREMENTS.md
- 00_PROJECT/DECISIONS.md
- 00_PROJECT/RISKS.md
- 99_MANAGEMENT/BUILD_MASTER.md
- 99_MANAGEMENT/CURRENT_STATUS.md
- 99_MANAGEMENT/ROADMAP.md
- the architecture document named in this prompt
- existing code/config/tests for the component

The repository is the source of truth. Do not invent existing files, APIs or services.

## Hard rules

- Corporate AI is local-first. Do not add cloud LLM inference.
- Qwen3.6 is the primary production LLM unless an approved registry decision says otherwise.
- Qdrant is an index, not canonical document storage.
- Documents and Web content are untrusted input.
- ACL/policy must be enforced outside the LLM.
- Do not silently resolve conflicting evidence.
- When evidence is insufficient, return a controlled insufficient-evidence result.
- Do not expose unrestricted Internet access to Qwen.
- Preserve existing working functionality.
- Do not delete data, volumes or services without explicit evidence that they are obsolete.
- Prefer small, testable services with explicit contracts.
- Pin versions where production reproducibility matters.
- Do not mark functionality complete until it is actually tested.

## Required workflow

1. Inspect repository and current implementation.
2. Identify what already exists and reuse it.
3. Write down the implementation delta.
4. Implement the smallest coherent production-quality increment.
5. Add/update unit and integration tests.
6. Build/run the component in the real Docker environment when applicable.
7. Test failure paths and resource limits.
8. Update relevant documentation.
9. Report exact files changed, tests run, results, remaining risks and next step.
10. Commit on a dedicated branch; do not rewrite unrelated history.

## Definition of done

The component is done only when:
- its API/contract is documented;
- configuration is reproducible;
- tests pass;
- health/readiness is defined;
- failure behavior is explicit;
- security boundaries are tested;
- provenance/audit requirements are met where applicable;
- integration points are tested;
- rollback/recovery is documented.


undefined