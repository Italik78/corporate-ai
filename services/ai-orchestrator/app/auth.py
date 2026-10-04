from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


async def require_gateway_service(authorization: str | None = Header(default=None)) -> str:
    expected = os.getenv("ORCHESTRATOR_GATEWAY_SERVICE_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="SERVICE_AUTH_NOT_CONFIGURED")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="SERVICE_AUTH_REQUIRED")
    if not hmac.compare_digest(authorization[7:], expected):
        raise HTTPException(status_code=401, detail="INVALID_SERVICE_CREDENTIAL")
    return "gateway"
