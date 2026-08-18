"""Vendor/category spend history, read from the ledger.

Both real and synthetic-seed rows count toward history -- that's the point of
the synthetic seed data (see seed/generate_synthetic_seed.py): it gives the
anomaly module something to compare against from the very first real run.
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass, field

from app.models.ledger import LedgerRecord
from app.services.sheets_client import SheetsClient


@dataclass
class VendorHistory:
    vendor_name: str
    invoices: list[LedgerRecord] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.invoices)

    @property
    def mean_amount(self) -> float:
        return statistics.mean(r.total for r in self.invoices) if self.invoices else 0.0

    @property
    def stdev_amount(self) -> float:
        if len(self.invoices) < 2:
            return 0.0
        return statistics.pstdev(r.total for r in self.invoices)


@dataclass
class CategoryHistory:
    category: str
    invoices: list[LedgerRecord] = field(default_factory=list)

    def monthly_totals(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for r in self.invoices:
            key = f"{r.invoice_date.year:04d}-{r.invoice_date.month:02d}"
            totals[key] = totals.get(key, 0.0) + r.total
        return totals

    def historical_monthly_average(self, exclude_month: str) -> float:
        totals = self.monthly_totals()
        totals.pop(exclude_month, None)
        if not totals:
            return 0.0
        return statistics.mean(totals.values())


def get_vendor_history(vendor_name: str, sheets_client: SheetsClient) -> VendorHistory:
    all_records = sheets_client.get_all_records()
    matches = [r for r in all_records if r.vendor_name.strip().lower() == vendor_name.strip().lower()]
    return VendorHistory(vendor_name=vendor_name, invoices=matches)


def get_category_history(category: str, sheets_client: SheetsClient) -> CategoryHistory:
    all_records = sheets_client.get_all_records()
    matches = [r for r in all_records if (r.category or "").strip().lower() == category.strip().lower()]
    return CategoryHistory(category=category, invoices=matches)


def current_month_key(as_of: dt.date | None = None) -> str:
    d = as_of or dt.date.today()
    return f"{d.year:04d}-{d.month:02d}"
