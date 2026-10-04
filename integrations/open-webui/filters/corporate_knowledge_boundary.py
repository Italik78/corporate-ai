"""
title: Corporate Knowledge Boundary
author: Corporate AI
version: 1.0.0
description: Prevents Open WebUI native file and Knowledge retrieval in the Corporate AI model.
"""

from __future__ import annotations

from typing import Any


def remove_native_knowledge_references(body: Any) -> Any:
    """Remove request-scoped file/Knowledge attachments without touching stored data.

    Open WebUI resolves ``files`` and ``metadata.files`` into local Chroma or
    external Knowledge retrieval before forwarding the request to the model.
    The Corporate AI model must use the Gateway → Orchestrator → Knowledge
    Engine path instead. The request envelope is copied so this filter never
    mutates the caller's object or any persisted Open WebUI file/Knowledge row.
    """
    if not isinstance(body, dict):
        return body

    filtered = dict(body)
    filtered.pop("files", None)

    metadata = filtered.get("metadata")
    if isinstance(metadata, dict):
        filtered_metadata = dict(metadata)
        filtered_metadata.pop("files", None)
        filtered_metadata.pop("folder_knowledge", None)
        filtered["metadata"] = filtered_metadata

    return filtered


class Filter:
    # Open WebUI's Filter runner also strips request files when this flag is
    # true. Keep the explicit inlet cleanup above as defense in depth.
    file_handler = True

    def inlet(
        self,
        body: dict[str, Any],
        __metadata__: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        filtered = remove_native_knowledge_references(body)

        # Folder Knowledge is added to request metadata before the filter inlet
        # and can be consumed by Open WebUI's native Knowledge tools later.
        # Strip this per-request reference as well; stored folder contents are
        # untouched and remain available outside the Corporate AI model.
        if isinstance(__metadata__, dict):
            __metadata__.pop("files", None)
            __metadata__.pop("folder_knowledge", None)

        return filtered
