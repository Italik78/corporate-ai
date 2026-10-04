import asyncio
import pytest
from fastapi import HTTPException

from app.auth import require_gateway_service


def test_gateway_service_auth_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_GATEWAY_SERVICE_TOKEN", raising=False)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_gateway_service(None))
    assert exc.value.status_code == 503


def test_gateway_service_auth_rejects_missing_or_invalid_token(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_GATEWAY_SERVICE_TOKEN", "expected-secret")
    with pytest.raises(HTTPException) as missing:
        asyncio.run(require_gateway_service(None))
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as wrong:
        asyncio.run(require_gateway_service("Bearer wrong-secret"))
    assert wrong.value.status_code == 401


def test_gateway_service_auth_accepts_configured_gateway(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_GATEWAY_SERVICE_TOKEN", "expected-secret")
    assert asyncio.run(require_gateway_service("Bearer expected-secret")) == "gateway"
