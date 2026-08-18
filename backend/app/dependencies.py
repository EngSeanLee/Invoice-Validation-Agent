"""Shared FastAPI dependencies."""

from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings
from app.services.sheets_client import GoogleSheetsClient, SheetsClient


@lru_cache
def _sheets_client_singleton() -> SheetsClient:
    """Built once per process and reused across requests -- lazy rather than
    built at app startup (see main.py) so it works the same way whether the
    process lives for hours (local uvicorn) or is a fresh serverless instance
    per cold start (Vercel): either way, first request pays the Google auth
    cost, every request after reuses it."""
    settings = get_settings()
    service_account_info = settings.resolve_service_account_info()
    client = GoogleSheetsClient(settings.sheet_id, service_account_info)
    try:
        client.ensure_headers()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Failed to connect to the Google Sheets ledger: {exc}. Check "
                "GOOGLE_SERVICE_ACCOUNT_JSON and SHEET_ID, and confirm the target "
                "Sheet is shared with the service account's client_email as Editor."
            ),
        ) from exc
    return client


def get_sheets_client() -> SheetsClient:
    """Swappable for a MockSheetsClient in tests via FastAPI's
    dependency_overrides (tests never call this -- they construct
    MockSheetsClient directly and pass it to the service functions)."""
    return _sheets_client_singleton()


def require_passphrase(
    settings: Settings = Depends(get_settings),
    x_app_passphrase: str | None = Header(None, alias="X-App-Passphrase"),
) -> None:
    """Gate for public deployments (see routers/auth.py). A no-op when
    APP_PASSPHRASE isn't configured -- local/dev runs stay ungated."""
    if settings.app_passphrase and x_app_passphrase != settings.app_passphrase:
        raise HTTPException(status_code=401, detail="Invalid or missing passphrase.")
