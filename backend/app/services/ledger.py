"""write_ledger_record() / resolve_flag() / get_ledger() -- the ledger-facing
tool functions from the spec. Thin wrappers around a SheetsClient so routers
stay free of Sheets-specific logic."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from app.models.invoice import InvoiceExtraction, ValidationResult
from app.models.ledger import LedgerRecord
from app.services.sheets_client import SheetsClient


def write_ledger_record(
    extraction: InvoiceExtraction,
    validation: ValidationResult,
    status: str,
    flag_reasons: list[str],
    sheets_client: SheetsClient,
    source: str = "Real",
) -> LedgerRecord:
    """Writes a record with the *recomputed* canonical totals -- never the raw
    model-extracted total -- per the spec's "never trust extracted totals"
    requirement."""
    record = LedgerRecord(
        id=str(uuid.uuid4()),
        vendor_name=extraction.vendor_name,
        invoice_number=extraction.invoice_number,
        invoice_date=extraction.invoice_date,
        total=validation.recomputed_total,
        category=extraction.category,
        status=status,
        flag_reasons=flag_reasons,
        reviewed_by=None,
        reviewed_date=None,
        source=source,
    )
    sheets_client.append_record(record)
    return record


def resolve_flag(invoice_id: str, reviewer: str, sheets_client: SheetsClient) -> Optional[LedgerRecord]:
    return sheets_client.update_record(
        invoice_id,
        {
            "status": "Resolved",
            "reviewed_by": reviewer,
            "reviewed_date": dt.date.today(),
        },
    )


def get_ledger(sheets_client: SheetsClient) -> list[LedgerRecord]:
    return sheets_client.get_all_records()
