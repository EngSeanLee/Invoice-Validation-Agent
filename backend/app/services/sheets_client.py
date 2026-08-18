"""Google Sheets ledger backend.

Uses the Sheets API (google-api-python-client) + a service-account credential
directly -- not Apps Script -- since that's simpler to drive headlessly from a
backend service.

`SheetsClient` is a Protocol so the rest of the app (services/ledger.py,
services/history.py) depends on an interface, not a concrete Google client.
`MockSheetsClient` is an in-memory stand-in used by tests and by the build
smoke-test, so the extract -> validate -> anomaly -> ledger pipeline is
provable without live Google credentials.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional, Protocol

from app.models.ledger import LedgerRecord

# Column order in the underlying Sheet -- keep in sync with LedgerRecord fields.
LEDGER_COLUMNS = [
    "ID",
    "Vendor",
    "Invoice #",
    "Date",
    "Total",
    "Category",
    "Status",
    "Flag Reason(s)",
    "Reviewed By",
    "Reviewed Date",
    "Source",
]

SHEET_RANGE_NAME = "Ledger"  # tab name; header row is row 1, data starts row 2


def _record_to_row(record: LedgerRecord) -> list[str]:
    return [
        record.id,
        record.vendor_name,
        record.invoice_number,
        record.invoice_date.isoformat(),
        f"{record.total:.2f}",
        record.category or "",
        record.status,
        "; ".join(record.flag_reasons),
        record.reviewed_by or "",
        record.reviewed_date.isoformat() if record.reviewed_date else "",
        record.source,
    ]


def _row_to_record(row: list[str]) -> Optional[LedgerRecord]:
    # Pad short rows (trailing empty cells are often omitted by the Sheets API).
    padded = row + [""] * (len(LEDGER_COLUMNS) - len(row))
    (
        id_, vendor, invoice_number, date_str, total_str, category,
        status, flag_reasons_str, reviewed_by, reviewed_date_str, source,
    ) = padded[: len(LEDGER_COLUMNS)]

    if not id_:
        return None

    return LedgerRecord(
        id=id_,
        vendor_name=vendor,
        invoice_number=invoice_number,
        invoice_date=dt.date.fromisoformat(date_str) if date_str else dt.date.today(),
        total=float(total_str) if total_str else 0.0,
        category=category or None,
        status=status or "Clean",
        flag_reasons=[r for r in flag_reasons_str.split("; ") if r] if flag_reasons_str else [],
        reviewed_by=reviewed_by or None,
        reviewed_date=dt.date.fromisoformat(reviewed_date_str) if reviewed_date_str else None,
        source=source or "Real",
    )


class SheetsClient(Protocol):
    def ensure_headers(self) -> None: ...

    def get_all_records(self) -> list[LedgerRecord]: ...

    def append_record(self, record: LedgerRecord) -> None: ...

    def update_record(self, invoice_id: str, updates: dict) -> Optional[LedgerRecord]: ...


class GoogleSheetsClient:
    """Real Sheets-API-backed ledger. Requires a service account with Editor
    access on the target spreadsheet (see README setup steps)."""

    def __init__(self, sheet_id: str, service_account_info: dict):
        # Imported lazily so environments without google-api-python-client
        # installed (e.g. a minimal test run) don't fail at import time.
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        self._service = build("sheets", "v4", credentials=credentials)
        self._sheet_id = sheet_id

    def _values(self):
        return self._service.spreadsheets().values()

    def ensure_headers(self) -> None:
        result = (
            self._values()
            .get(spreadsheetId=self._sheet_id, range=f"{SHEET_RANGE_NAME}!A1:K1")
            .execute()
        )
        existing = result.get("values", [[]])[0] if result.get("values") else []
        if existing != LEDGER_COLUMNS:
            self._values().update(
                spreadsheetId=self._sheet_id,
                range=f"{SHEET_RANGE_NAME}!A1:K1",
                valueInputOption="RAW",
                body={"values": [LEDGER_COLUMNS]},
            ).execute()

    def get_all_records(self) -> list[LedgerRecord]:
        result = (
            self._values()
            .get(spreadsheetId=self._sheet_id, range=f"{SHEET_RANGE_NAME}!A2:K")
            .execute()
        )
        rows = result.get("values", [])
        records = [_row_to_record(row) for row in rows]
        return [r for r in records if r is not None]

    def append_record(self, record: LedgerRecord) -> None:
        self._values().append(
            spreadsheetId=self._sheet_id,
            range=f"{SHEET_RANGE_NAME}!A2:K",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [_record_to_row(record)]},
        ).execute()

    def update_record(self, invoice_id: str, updates: dict) -> Optional[LedgerRecord]:
        result = (
            self._values()
            .get(spreadsheetId=self._sheet_id, range=f"{SHEET_RANGE_NAME}!A2:K")
            .execute()
        )
        rows = result.get("values", [])
        for i, row in enumerate(rows):
            padded = row + [""] * (len(LEDGER_COLUMNS) - len(row))
            if padded[0] == invoice_id:
                record = _row_to_record(padded)
                if record is None:
                    return None
                updated = record.model_copy(update=updates)
                sheet_row_number = i + 2  # +1 for header, +1 for 1-indexing
                self._values().update(
                    spreadsheetId=self._sheet_id,
                    range=f"{SHEET_RANGE_NAME}!A{sheet_row_number}:K{sheet_row_number}",
                    valueInputOption="RAW",
                    body={"values": [_record_to_row(updated)]},
                ).execute()
                return updated
        return None


class MockSheetsClient:
    """In-memory ledger used by tests and by the pipeline smoke test -- lets
    the full extract -> validate -> anomaly -> ledger flow be proven without
    live Google credentials."""

    def __init__(self):
        self._records: dict[str, LedgerRecord] = {}

    def ensure_headers(self) -> None:
        pass  # nothing to do for an in-memory store

    def get_all_records(self) -> list[LedgerRecord]:
        # Preserve insertion order, like a real sheet's row order.
        return list(self._records.values())

    def append_record(self, record: LedgerRecord) -> None:
        self._records[record.id] = record

    def update_record(self, invoice_id: str, updates: dict) -> Optional[LedgerRecord]:
        existing = self._records.get(invoice_id)
        if existing is None:
            return None
        updated = existing.model_copy(update=updates)
        self._records[invoice_id] = updated
        return updated
