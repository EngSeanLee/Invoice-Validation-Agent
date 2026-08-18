import copy
import datetime as dt

from app.models.ledger import LedgerRecord
from app.services import anomaly
from app.services.history import CategoryHistory, VendorHistory
from app.services.validation import recompute_totals


def _empty_histories(vendor_name: str, category: str) -> tuple[VendorHistory, CategoryHistory]:
    return VendorHistory(vendor_name=vendor_name), CategoryHistory(category=category)


def test_single_new_vendor_signal_does_not_flag_alone(sample_extraction, settings):
    # ANOMALY_SIGNAL_THRESHOLD defaults to 2; new_vendor alone has weight 1.
    validated = recompute_totals(sample_extraction)
    vendor_hist, category_hist = _empty_histories(
        sample_extraction.vendor_name, sample_extraction.category
    )

    flags, is_flagged = anomaly.check_anomalies(
        sample_extraction, validated, vendor_hist, category_hist, [], settings
    )

    signal_names = {f.signal for f in flags}
    assert "new_vendor" in signal_names
    assert is_flagged is False  # combined signals required, not one rule alone


def test_math_mismatch_plus_new_vendor_combine_to_flag(sample_extraction, settings):
    bad = copy.deepcopy(sample_extraction)
    bad.total = 99999.0  # forces a math_mismatch signal
    validated = recompute_totals(bad)
    vendor_hist, category_hist = _empty_histories(bad.vendor_name, bad.category)

    flags, is_flagged = anomaly.check_anomalies(
        bad, validated, vendor_hist, category_hist, [], settings
    )

    signal_names = {f.signal for f in flags}
    assert {"new_vendor", "math_mismatch"}.issubset(signal_names)
    assert is_flagged is True


def test_duplicate_invoice_number_flags_alone(sample_extraction, settings):
    validated = recompute_totals(sample_extraction)
    existing = LedgerRecord(
        id="existing-1",
        vendor_name=sample_extraction.vendor_name,
        invoice_number=sample_extraction.invoice_number,
        invoice_date=dt.date(2026, 1, 1),
        total=1.0,
        category=sample_extraction.category,
        status="Clean",
        source="Real",
    )
    vendor_hist = VendorHistory(vendor_name=sample_extraction.vendor_name, invoices=[existing])
    category_hist = CategoryHistory(category=sample_extraction.category)

    flags, is_flagged = anomaly.check_anomalies(
        sample_extraction, validated, vendor_hist, category_hist, [existing], settings
    )

    assert any(f.signal == "duplicate_invoice" for f in flags)
    assert is_flagged is True  # weight 2 >= threshold 2, flags solo


def test_amount_above_vendor_avg_requires_minimum_history(sample_extraction, settings):
    validated = recompute_totals(sample_extraction)
    # Only 2 prior invoices -- below MIN_HISTORY_FOR_ZSCORE (3), so the
    # z-score signal should not fire even though the amount is way above avg.
    history_records = [
        LedgerRecord(
            id=f"h{i}", vendor_name=sample_extraction.vendor_name, invoice_number=f"H{i}",
            invoice_date=dt.date(2026, 1, i + 1), total=10.0, category=sample_extraction.category,
            status="Clean", source="Synthetic",
        )
        for i in range(2)
    ]
    vendor_hist = VendorHistory(vendor_name=sample_extraction.vendor_name, invoices=history_records)
    category_hist = CategoryHistory(category=sample_extraction.category)

    flags, _ = anomaly.check_anomalies(
        sample_extraction, validated, vendor_hist, category_hist, history_records, settings
    )

    assert "amount_above_vendor_avg" not in {f.signal for f in flags}


def test_clean_invoice_with_established_history_is_not_flagged(sample_extraction, settings):
    validated = recompute_totals(sample_extraction)
    # Established vendor with similar historical amounts -> no anomalies.
    history_records = [
        LedgerRecord(
            id=f"h{i}", vendor_name=sample_extraction.vendor_name, invoice_number=f"H{i}",
            invoice_date=dt.date(2026, 1, i + 1), total=135.0, category=sample_extraction.category,
            status="Clean", source="Synthetic",
        )
        for i in range(5)
    ]
    vendor_hist = VendorHistory(vendor_name=sample_extraction.vendor_name, invoices=history_records)
    category_hist = CategoryHistory(category=sample_extraction.category, invoices=history_records)

    flags, is_flagged = anomaly.check_anomalies(
        sample_extraction, validated, vendor_hist, category_hist, history_records, settings
    )

    assert flags == []
    assert is_flagged is False
