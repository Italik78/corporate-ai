from __future__ import annotations

import os
from enum import Enum

from .models import SourceClass


class SourcePolicyMode(str, Enum):
    INTERNAL_ONLY = "INTERNAL_ONLY"
    INTERNAL_FIRST_WEB_FALLBACK = "INTERNAL_FIRST_WEB_FALLBACK"
    EXPLICIT_WEB = "EXPLICIT_WEB"
    RESTRICTED_OFFLINE = "RESTRICTED_OFFLINE"


_MODE_SOURCES = {
    SourcePolicyMode.INTERNAL_ONLY: [SourceClass.CORPORATE],
    SourcePolicyMode.INTERNAL_FIRST_WEB_FALLBACK: [SourceClass.CORPORATE, SourceClass.WEB],
    SourcePolicyMode.EXPLICIT_WEB: [SourceClass.WEB],
    SourcePolicyMode.RESTRICTED_OFFLINE: [SourceClass.CORPORATE],
}


def configured_source_policy(value: str | None = None) -> tuple[SourcePolicyMode, list[SourceClass]]:
    """Resolve policy from trusted server configuration, never request JSON."""
    raw = (value if value is not None else os.getenv("CORPORATE_AI_SOURCE_POLICY", "INTERNAL_ONLY"))
    try:
        mode = SourcePolicyMode(raw.strip().upper())
    except ValueError as exc:
        raise ValueError(f"invalid CORPORATE_AI_SOURCE_POLICY: {raw}") from exc
    return mode, list(_MODE_SOURCES[mode])
