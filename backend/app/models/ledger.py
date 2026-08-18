"""Pydantic models for the Google Sheets ledger."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class LedgerRecord(BaseModel):
    """One row of the ledger. Column order here matches the Sheet header row --
    see services/sheets_client.py LEDGER_COLUMNS."""

    id: str
    vendor_name: str
    invoice_number: str
    invoice_date: date
    total: float
    category: Optional[str] = None
    status: str  # "Clean" | "Flagged" | "Resolved"
    flag_reasons: list[str] = []
    reviewed_by: Optional[str] = None
    reviewed_date: Optional[date] = None
    source: str = "Real"  # "Real" | "Synthetic" -- synthetic seed rows are always labeled


class ResolveRequest(BaseModel):
    reviewer: str
