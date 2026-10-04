import pytest
from fastapi import HTTPException

from app import main
from app.config import settings


def test_recovery_routes_fail_closed_when_token_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "recovery_token", "")
    with pytest.raises(HTTPException) as error:
        main._authorize_recovery(None)
    assert error.value.status_code == 503
    assert error.value.detail == "RECOVERY_NOT_CONFIGURED"


def test_recovery_routes_reject_wrong_token_and_accept_configured_token(monkeypatch):
    monkeypatch.setattr(settings, "recovery_token", "recovery-test-secret")
    with pytest.raises(HTTPException) as error:
        main._authorize_recovery("wrong")
    assert error.value.status_code == 401

    assert main._authorize_recovery("recovery-test-secret") is None
