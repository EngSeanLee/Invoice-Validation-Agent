"""Populate the ledger with synthetic vendor history so the anomaly module has
a realistic baseline from the very first real invoice (cold-start note in the
spec). All rows are written with Source=Synthetic and Status=Clean, and should
be clearly labeled as synthetic wherever the ledger is shown -- never
presented as real spend.

Usage:
    python -m app.seed.generate_synthetic_seed
"""

from __future__ import annotations

import datetime as dt
import random
import sys
import uuid

from app.config import get_settings
from app.models.ledger import LedgerRecord
from app.seed.synthetic_vendors import VENDOR_PROFILES
from app.services.sheets_client import SheetsClient

random.seed(42)  # reproducible synthetic data across runs


def _spread_dates(count: int, months_back: int = 6) -> list[dt.date]:
    """count roughly-evenly-spaced-but-jittered dates over the past months_back months."""
    today = dt.date.today()
    start = today - dt.timedelta(days=months_back * 30)
    span_days = (today - start).days
    dates = []
    for i in range(count):
        base_offset = int(span_days * (i + 0.5) / count)
        jitter = random.randint(-4, 4)
        offset = max(0, min(span_days, base_offset + jitter))
        dates.append(start + dt.timedelta(days=offset))
    return sorted(dates)


def generate_seed_records() -> list[LedgerRecord]:
    records: list[LedgerRecord] = []
    for profile in VENDOR_PROFILES:
        dates = _spread_dates(profile.invoice_count)
        for seq, invoice_date in enumerate(dates, start=1):
            amount = max(
                1.0,
                random.gauss(profile.mean_amount, profile.mean_amount * profile.stdev_fraction),
            )
            amount = round(amount, 2)
            records.append(
                LedgerRecord(
                    id=str(uuid.uuid4()),
                    vendor_name=profile.vendor_name,
                    invoice_number=f"{profile.invoice_code}-{seq:04d}",
                    invoice_date=invoice_date,
                    total=amount,
                    category=profile.category,
                    status="Clean",
                    flag_reasons=[],
                    reviewed_by=None,
                    reviewed_date=None,
                    source="Synthetic",
                )
            )
    return records


def seed(sheets_client: SheetsClient) -> int:
    sheets_client.ensure_headers()
    records = generate_seed_records()
    for record in records:
        sheets_client.append_record(record)
    return len(records)


def main() -> None:
    settings = get_settings()
    from app.services.sheets_client import GoogleSheetsClient

    service_account_info = settings.resolve_service_account_info()
    sheets_client = GoogleSheetsClient(settings.sheet_id, service_account_info)
    count = seed(sheets_client)
    print(f"Seeded {count} synthetic invoices across {len(VENDOR_PROFILES)} vendors.")
    print("These rows are labeled Source=Synthetic in the ledger -- not real spend.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"Seed generation failed: {exc}", file=sys.stderr)
        sys.exit(1)
