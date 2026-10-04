"""Fail-closed internal service authentication for the Knowledge Engine.

Credentials are deployment supplied as JSON in
KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS. No credential is baked into the image.
Each entry maps a service name to a token and an explicit retrieval policy.
"""

from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class ServicePrincipal:
    service: str
    permissions: frozenset[str]
    access_scopes: tuple[str, ...]
    classifications: tuple[str, ...]
    project_ids: tuple[str, ...]


def _credentials() -> dict:
    raw = os.getenv("KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS", "").strip()
    if not raw:
        raise HTTPException(status_code=503, detail="SERVICE_AUTH_NOT_CONFIGURED")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="INVALID_SERVICE_AUTH_CONFIG") from exc
    if not isinstance(value, dict) or not value:
        raise HTTPException(status_code=503, detail="INVALID_SERVICE_AUTH_CONFIG")
    return value


def _principal(service: str, entry: object) -> ServicePrincipal | None:
    if not isinstance(entry, dict):
        return None
    token = entry.get("token")
    permissions = entry.get("permissions")
    scopes = entry.get("access_scopes")
    classifications = entry.get("classifications")
    projects = entry.get("project_ids")
    if not isinstance(token, str) or not token:
        return None
    # An omitted/empty policy is a configuration error, never an allow-all.
    if not isinstance(scopes, list) or not scopes:
        return None
    if not isinstance(classifications, list) or not classifications:
        return None
    if not isinstance(projects, list) or not projects:
        return None
    if not isinstance(permissions, list) or not permissions:
        return None
    return ServicePrincipal(
        service=service,
        permissions=frozenset(str(item) for item in permissions),
        access_scopes=tuple(str(item) for item in scopes),
        classifications=tuple(str(item) for item in classifications),
        project_ids=tuple(str(item) for item in projects),
    )


def service_auth(permission: str):
    async def dependency(
        authorization: str | None = Header(default=None),
    ) -> ServicePrincipal:
        return authenticate_service(authorization, permission)

    return dependency


def authenticate_service(
    authorization: str | None,
    permission: str,
) -> ServicePrincipal:
    configured = _credentials()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="SERVICE_AUTH_REQUIRED")
    supplied = authorization[7:]
    matched: ServicePrincipal | None = None
    for service, entry in configured.items():
        principal = _principal(str(service), entry)
        if principal is not None and hmac.compare_digest(entry["token"], supplied):
            matched = principal
    if matched is None:
        raise HTTPException(status_code=401, detail="INVALID_SERVICE_CREDENTIAL")
    if permission not in matched.permissions:
        raise HTTPException(status_code=403, detail="SERVICE_PERMISSION_DENIED")
    return matched
