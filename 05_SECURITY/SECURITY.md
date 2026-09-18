# SECURITY

Threat model: documents are untrusted; document content can contain prompt injection; tools can have side effects; model output is not authority.

Controls: local model execution; tool allowlist/policy; schema validation; path restrictions; approval gates for high-impact operations; provenance and audit logging; resource limits; no uncontrolled model Internet access.