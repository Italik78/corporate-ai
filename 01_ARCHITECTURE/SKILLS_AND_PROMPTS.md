# SKILLS AND PROMPTS

## Purpose

Skills and prompts are first-class, versioned components of Corporate AI.

They must not be hidden inside application code or improvised by the LLM.

## Skill

A skill is a reusable capability definition.

Example skills:
- contract_analysis
- web_research
- procurement_documentation
- document_summary
- financial_analysis
- meeting_analysis
- report_generation

A skill defines:
- id/name
- description
- trigger/selection criteria
- inputs
- outputs
- allowed tools
- required knowledge scopes
- prompt references
- policies
- dependencies
- validation
- version
- status

## Prompt

A prompt is an independently versioned instruction artifact.

Prompt classes:
- system
- policy
- agent
- skill
- research
- extraction
- vision
- answer synthesis
- tool-use
- validation

Prompts are stored in a Prompt Registry and referenced by immutable version.

## Separation

```
Skill
 ├── capability contract
 ├── tools
 ├── policy
 ├── inputs/outputs
 └── Prompt references

Prompt
 └── instruction content/version
```

Changing wording in a prompt must not silently change the skill contract.

## Lifecycle

```
draft → tested → candidate → production → deprecated
```

Production versions are immutable.

## Skill execution

Before execution:
- user permission checked
- required data scopes checked
- required tools available
- required model available
- prompt versions resolved
- resource limits checked

After execution:
- output schema validated
- evidence/provenance attached
- tool calls audited
- result evaluated

## Security

Skill and prompt content are trusted configuration.

Document content, Web content and tool output are untrusted data.

Untrusted content must never be able to overwrite:
- system policy
- ACL
- tool policy
- prompt registry
- skill configuration

## Testing

Every production skill needs:
- representative inputs
- expected output schema
- negative cases
- permission tests
- tool-failure tests
- evidence/grounding tests where applicable
- regression evaluation

## Model compatibility

Skills should declare compatible model capabilities rather than hard-coding one model where possible.

Qwen3.6 is the initial primary model. Alternative models remain experimental until evaluation proves a need.

## Acceptance criteria

A skill is production-ready only when its:
- contract
- prompt versions
- dependencies
- policy
- tests
- observability
- rollback/deprecation path

are documented.
