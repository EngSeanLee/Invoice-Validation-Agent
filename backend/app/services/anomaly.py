"""check_anomalies(): multi-signal anomaly detection.

Per the spec, flags fire on *combinations* of signals, not any single rule
alone -- this reduces noise from one-off legitimate outliers. Each signal is
an independent, swappable function returning an AnomalyFlag (or None). Their
weights are summed and compared against ANOMALY_SIGNAL_THRESHOLD; a duplicate
invoice number is weighted high enough to flag on its own (high confidence,
not really the "combine signals" case the spec is guarding against).

To add a new signal: write a function with the `SignalFn` shape and add it to
SIGNALS. To change how signals combine, edit only `check_anomalies` -- callers
don't need to know how the combination policy works.
"""

from __future__ import annotations

from typing import Callable, Optional

from app.config import Settings
from app.models.invoice import AnomalyFlag, InvoiceExtraction, ValidationResult
from app.models.ledger import LedgerRecord
from app.services.history import CategoryHistory, VendorHistory, current_month_key

MIN_HISTORY_FOR_ZSCORE = 3


class AnomalyContext:
    def __init__(
        self,
        extraction: InvoiceExtraction,
        validation: ValidationResult,
        vendor_history: VendorHistory,
        category_history: CategoryHistory,
        all_records: list[LedgerRecord],
        settings: Settings,
    ):
        self.extraction = extraction
        self.validation = validation
        self.vendor_history = vendor_history
        self.category_history = category_history
        self.all_records = all_records
        self.settings = settings
        # The recomputed total, not the model's raw extracted total -- every
        # amount-based signal below must compare against this. Using
        # extraction.total here would defeat the point of validation.py: an
        # invoice with wrong printed math would get judged against a number
        # we already know not to trust.
        self.canonical_total = validation.recomputed_total


SignalFn = Callable[[AnomalyContext], Optional[AnomalyFlag]]


def signal_amount_above_vendor_avg(ctx: AnomalyContext) -> Optional[AnomalyFlag]:
    vh = ctx.vendor_history
    if vh.count < MIN_HISTORY_FOR_ZSCORE or vh.stdev_amount == 0:
        return None  # cold start handled by synthetic seed data, not special-cased here
    z_score = (ctx.canonical_total - vh.mean_amount) / vh.stdev_amount
    if z_score >= ctx.settings.anomaly_zscore_threshold:
        return AnomalyFlag(
            signal="amount_above_vendor_avg",
            reason=(
                f"Total ${ctx.canonical_total:.2f} is {z_score:.1f} standard deviations "
                f"above {vh.vendor_name}'s historical average (${vh.mean_amount:.2f}, "
                f"n={vh.count})"
            ),
            weight=1,
        )
    return None


def signal_new_vendor(ctx: AnomalyContext) -> Optional[AnomalyFlag]:
    if ctx.vendor_history.count == 0:
        return AnomalyFlag(
            signal="new_vendor",
            reason=f"'{ctx.extraction.vendor_name}' has no prior invoices in the ledger",
            weight=1,
        )
    return None


def signal_duplicate_invoice(ctx: AnomalyContext) -> Optional[AnomalyFlag]:
    for r in ctx.all_records:
        same_vendor = r.vendor_name.strip().lower() == ctx.extraction.vendor_name.strip().lower()
        if not same_vendor:
            continue
        if r.invoice_number.strip() == ctx.extraction.invoice_number.strip():
            return AnomalyFlag(
                signal="duplicate_invoice",
                reason=(
                    f"Invoice number '{ctx.extraction.invoice_number}' already exists in "
                    f"the ledger for {r.vendor_name}"
                ),
                weight=2,  # high confidence -- can flag alone
            )
        same_amount = abs(r.total - ctx.canonical_total) < 0.01
        same_date = r.invoice_date == ctx.extraction.invoice_date
        if same_amount and same_date:
            return AnomalyFlag(
                signal="duplicate_invoice",
                reason=(
                    f"Same vendor, amount (${r.total:.2f}), and date "
                    f"({r.invoice_date.isoformat()}) already exist in the ledger"
                ),
                weight=2,
            )
    return None


def signal_category_trend(ctx: AnomalyContext) -> Optional[AnomalyFlag]:
    if not ctx.extraction.category:
        return None
    ch = ctx.category_history
    month = current_month_key(ctx.extraction.invoice_date)
    monthly_totals = ch.monthly_totals()
    current_month_total = monthly_totals.get(month, 0.0) + ctx.canonical_total
    avg = ch.historical_monthly_average(exclude_month=month)
    if avg <= 0:
        return None
    ratio = current_month_total / avg
    if ratio >= 1.5:
        return AnomalyFlag(
            signal="category_trend",
            reason=(
                f"'{ctx.extraction.category}' spend this month (${current_month_total:.2f}) "
                f"is {ratio:.1f}x the historical monthly average (${avg:.2f})"
            ),
            weight=1,
        )
    return None


def signal_math_mismatch(ctx: AnomalyContext) -> Optional[AnomalyFlag]:
    if ctx.validation.math_mismatch:
        return AnomalyFlag(
            signal="math_mismatch",
            reason="Recomputed totals don't match the extracted invoice math: "
            + "; ".join(ctx.validation.discrepancies),
            weight=1,
        )
    return None


SIGNALS: list[SignalFn] = [
    signal_amount_above_vendor_avg,
    signal_new_vendor,
    signal_duplicate_invoice,
    signal_category_trend,
    signal_math_mismatch,
]


class AnomalyDetector:
    """Single entry point for anomaly checking -- the combination policy
    (weighted-sum-vs-threshold) lives here so it can be swapped later without
    touching callers or the individual signal functions."""

    def __init__(self, signals: list[SignalFn] = SIGNALS):
        self._signals = signals

    def check(self, ctx: AnomalyContext) -> tuple[list[AnomalyFlag], bool]:
        """Returns (triggered_flags, is_flagged)."""
        triggered = [flag for flag in (signal(ctx) for signal in self._signals) if flag]
        total_weight = sum(f.weight for f in triggered)
        is_flagged = total_weight >= ctx.settings.anomaly_signal_threshold
        return triggered, is_flagged


def check_anomalies(
    extraction: InvoiceExtraction,
    validation: ValidationResult,
    vendor_history: VendorHistory,
    category_history: CategoryHistory,
    all_records: list[LedgerRecord],
    settings: Settings,
) -> tuple[list[AnomalyFlag], bool]:
    ctx = AnomalyContext(
        extraction=extraction,
        validation=validation,
        vendor_history=vendor_history,
        category_history=category_history,
        all_records=all_records,
        settings=settings,
    )
    return AnomalyDetector().check(ctx)
