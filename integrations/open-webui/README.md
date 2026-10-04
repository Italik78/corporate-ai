# Open WebUI Corporate Knowledge Boundary

This Filter prevents the Corporate AI model from resolving attached files or
Knowledge collections through Open WebUI's native retrieval path. Corporate
knowledge requests must instead use the configured Corporate AI Gateway and
its Orchestrator → Knowledge Engine → Qdrant path.

The Filter removes only `files` references from the incoming request body and
`metadata.files` and request-scoped `folder_knowledge`. Open WebUI's Filter API
then applies its `file_handler` hook, which also drops file fields before
native file retrieval. This covers the chat file/collection path including
full-context mode; it does not delete or modify uploaded files, Chroma
collections, Knowledge records, or other persisted user data. Local files
remain available to models that do not have this Filter assigned.

## Install and bind

The current Open WebUI runtime is `0.11.4`. Install
[`filters/corporate_knowledge_boundary.py`](filters/corporate_knowledge_boundary.py)
as an administrator-created Filter Function, activate it, and assign it only
to the `corporate-ai` model. Apply the required model metadata patch in
[`config/corporate-ai-model-knowledge-boundary.json`](config/corporate-ai-model-knowledge-boundary.json): no attached native Knowledge, no built-in file/Knowledge tools, and file upload tools disabled. Keep `file_context` enabled so Open WebUI does not reinterpret chat attachments as an attached Knowledge tool; the Filter removes attachment references before retrieval. Do not enable the Filter globally: model-scoped assignment preserves local file and Knowledge retrieval for other models.

The current runtime has no installed Filter Functions and the `corporate-ai`
model has no `filterIds` binding. This artifact is therefore not active until
an administrator performs that UI configuration. Runtime configuration was
not changed as part of adding this artifact.

## Scope and acceptance

- Corporate model requests cannot carry Open WebUI file or Knowledge
  references into native Chroma/External Knowledge retrieval.
- Existing Open WebUI data remains unchanged and user-local retrieval remains
  available through models without this Filter.
- The corporate model has no native Knowledge binding or built-in file/Knowledge
  tool capability, preventing a second retrieval route after the Filter inlet.
- The Corporate AI model continues through the Gateway; the filter does not
  replace Gateway authorization or Knowledge Engine lifecycle/access checks.
- The current runtime has `rag.bypass_embedding_and_retrieval=true` and
  `rag.full_context=true`; therefore disabling only vector lookup is
  insufficient. The boundary removes the attachment references before either
  chunked retrieval or full-context file loading can occur.

Run the artifact tests from the repository root:

```sh
python -m unittest discover -s integrations/open-webui/tests -v
```

After UI activation, verify that the `corporate-ai` model has the Filter bound,
that a request with both a `file` and a `collection` attachment reaches the
Gateway without `files` references, and that a non-Corporate model still
retrieves its own local file. Do not delete existing Chroma or Knowledge data
as part of this verification.
