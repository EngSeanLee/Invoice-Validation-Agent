"""App configuration, loaded once at startup.

Required env vars are validated eagerly (see get_settings() / main.py) so a
missing credential fails fast with a clear message pointing at the README,
instead of an obscure traceback on the first real request.
"""

import json
import sys
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Required ---
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    google_service_account_json: str = Field(..., alias="GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id: str = Field(..., alias="SHEET_ID")

    # --- Optional / tunable ---
    # Haiku by default -- invoice extraction is a well-specified structured-JSON
    # task, not open-ended reasoning, so the cheaper/faster model is the right
    # default here. Override via CLAUDE_MODEL if you need higher accuracy on
    # messy scans (e.g. claude-sonnet-5 or claude-opus-5).
    claude_model: str = Field("claude-haiku-4-5", alias="CLAUDE_MODEL")
    anomaly_zscore_threshold: float = Field(2.0, alias="ANOMALY_ZSCORE_THRESHOLD")
    anomaly_signal_threshold: int = Field(2, alias="ANOMALY_SIGNAL_THRESHOLD")
    cors_allowed_origins: str = Field("http://localhost:5173", alias="CORS_ALLOWED_ORIGINS")
    # Optional shared-passphrase gate for public deployments (see routers/auth.py
    # and dependencies.require_passphrase). Unset -> no gate, e.g. local dev.
    app_passphrase: Optional[str] = Field(None, alias="APP_PASSPHRASE")

    @field_validator("anthropic_api_key", "google_service_account_json", "sheet_id")
    @classmethod
    def not_blank(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} is set but empty")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    def resolve_service_account_info(self) -> dict:
        """GOOGLE_SERVICE_ACCOUNT_JSON may be raw JSON content or a path to a key file."""
        raw = self.google_service_account_json
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            with open(raw, "r", encoding="utf-8") as f:
                return json.load(f)


SETUP_HINT = (
    "\n"
    "Missing or invalid required configuration.\n"
    "The Invoice Validation Agent backend needs ANTHROPIC_API_KEY, "
    "GOOGLE_SERVICE_ACCOUNT_JSON, and SHEET_ID set (via environment variables or "
    "backend/.env).\n"
    "See the 'Setup' section of the project README for step-by-step instructions, "
    "including how to create the Google Cloud service account and share the Sheet.\n"
)


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception as exc:  # pydantic ValidationError, mainly
        print(SETUP_HINT, file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def get_settings_for_tests(**overrides) -> Settings:
    """Bypass the cached, fail-fast get_settings() for unit tests.

    Explicitly disables the .env file source (_env_file=None) -- otherwise
    any field not passed in `overrides` silently falls back to whatever
    happens to be in the real backend/.env on disk (e.g. a developer's own
    APP_PASSPHRASE), making test behavior depend on local machine state
    instead of being hermetic.
    """
    defaults = {
        "ANTHROPIC_API_KEY": "test-key",
        "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "SHEET_ID": "test-sheet-id",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)
