import pytest
from fastapi import HTTPException

from app.config import get_settings_for_tests
from app.dependencies import require_passphrase
from app.routers.auth import AuthCheckRequest, check_passphrase


def test_no_gate_when_passphrase_unconfigured():
    settings = get_settings_for_tests()  # APP_PASSPHRASE unset by default
    # Should not raise, regardless of header value (including None/missing).
    require_passphrase(settings=settings, x_app_passphrase=None)
    require_passphrase(settings=settings, x_app_passphrase="anything")


def test_gate_rejects_missing_or_wrong_passphrase():
    settings = get_settings_for_tests(APP_PASSPHRASE="letmein")

    with pytest.raises(HTTPException) as exc:
        require_passphrase(settings=settings, x_app_passphrase=None)
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        require_passphrase(settings=settings, x_app_passphrase="wrong")
    assert exc.value.status_code == 401


def test_gate_accepts_correct_passphrase():
    settings = get_settings_for_tests(APP_PASSPHRASE="letmein")
    require_passphrase(settings=settings, x_app_passphrase="letmein")  # no raise


def test_auth_check_endpoint_reports_not_required(monkeypatch):
    settings = get_settings_for_tests()  # unset
    monkeypatch.setattr("app.routers.auth.get_settings", lambda: settings)

    result = check_passphrase(AuthCheckRequest(passphrase=""))
    assert result.required is False


def test_auth_check_endpoint_validates_passphrase(monkeypatch):
    settings = get_settings_for_tests(APP_PASSPHRASE="letmein")
    monkeypatch.setattr("app.routers.auth.get_settings", lambda: settings)

    result = check_passphrase(AuthCheckRequest(passphrase="letmein"))
    assert result.required is True

    with pytest.raises(HTTPException) as exc:
        check_passphrase(AuthCheckRequest(passphrase="wrong"))
    assert exc.value.status_code == 401
