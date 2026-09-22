# MODEL REGISTRY

## Purpose

All production AI models and their runtime configurations are versioned and identifiable.

The registry prevents a running service from depending on undocumented model state.

## Model record

Minimum:
- model_id
- model_name
- version/revision
- artifact location
- format/quantization
- capabilities
- context limit
- tokenizer/template version
- runtime
- resource profile
- status
- checksum where applicable
- owner
- approval metadata

## Runtime configuration

Configuration is versioned separately or as an immutable model deployment record.

It includes:
- served name
- endpoint
- context length
- GPU memory policy
- KV cache type
- reasoning/tool parsers
- sampling defaults
- feature flags
- dependency versions

## Lifecycle

lab → candidate → production → deprecated

Production records are immutable.

## Initial production model

Qwen3.6-35B-A3B-NVFP4 is the initial primary production LLM.

Embedding and reranking models have separate registry records because they are specialized capabilities.

## Model selection

Agent/Router may select a model only from an approved registry state.

Skills declare required capabilities, not arbitrary external model URLs.

## Acceptance

A model deployment is accepted only when:
- artifact is available locally
- version is recorded
- configuration is reproducible
- health check passes
- benchmark/validation passes
- rollback target exists
