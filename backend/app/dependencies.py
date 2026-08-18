"""Shared FastAPI dependencies."""

from fastapi import Request

from app.services.sheets_client import SheetsClient


def get_sheets_client(request: Request) -> SheetsClient:
    """The ledger backend, initialized once at startup (see main.py lifespan)
    and stashed on app.state -- swappable for a MockSheetsClient in tests via
    FastAPI's dependency_overrides."""
    return request.app.state.sheets_client
