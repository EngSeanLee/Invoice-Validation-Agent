"""End-to-end pipeline smoke test: extract -> validate -> anomaly -> ledger
write, all mocked (no live Anthropic or Google credentials required). This is
what "the build works" is verified against before pushing.
"""

import datetime as dt

from app.models.invoice import InvoiceExtraction, LineItem
from app.services import anomaly, extraction, history, ledger, validation
from tests.fixtures.generate_sample_invoice import build_sample_invoice_pdf


class _FakeParseResponse:
    def __init__(self, parsed_output):
        self.parsed_output = parsed_output


class _FakeMessages:
    def __init__(self, canned: InvoiceExtraction):
        self._canned = canned

    def parse(self, **kwargs):
        return _FakeParseResponse(self._canned)


class _FakeAnthropicClient:
    def __init__(self, canned: InvoiceExtraction):
        self.messages = _FakeMessages(canned)


def test_full_pipeline_clean_invoice(monkeypatch, settings, sheets_client, sample_extraction):
    monkeypatch.setattr(
        extraction, "_client", lambda settings: _FakeAnthropicClient(sample_extraction)
    )

    pdf_bytes = build_sample_invoice_pdf()
    extracted = extraction.extract_invoice(pdf_bytes, "application/pdf", settings)
    assert extracted == sample_extraction

    validated = validation.recompute_totals(extracted)
    assert validated.math_mismatch is False

    vendor_hist = history.get_vendor_history(extracted.vendor_name, sheets_client)
    category_hist = history.get_category_history(extracted.category, sheets_client)
    all_records = sheets_client.get_all_records()

    flags, is_flagged = anomaly.check_anomalies(
        extracted, validated, vendor_hist, category_hist, all_records, settings
    )
    status = "Flagged" if is_flagged else "Clean"
    flag_reasons = [f.reason for f in flags] if is_flagged else []

    record = ledger.write_ledger_record(
        extracted, validated, status, flag_reasons, sheets_client
    )

    stored = sheets_client.get_all_records()
    assert len(stored) == 1
    assert stored[0].id == record.id
    assert stored[0].vendor_name == "Acme Testing Co"
    assert stored[0].total == 135.0  # recomputed total, not raw model output
    assert stored[0].status == status


def test_full_pipeline_flags_bad_math(monkeypatch, settings, sheets_client, sample_extraction):
    broken = sample_extraction.model_copy(deep=True)
    broken.total = 99999.0  # forces math_mismatch, combined with new_vendor -> flagged

    monkeypatch.setattr(extraction, "_client", lambda settings: _FakeAnthropicClient(broken))

    pdf_bytes = build_sample_invoice_pdf()
    extracted = extraction.extract_invoice(pdf_bytes, "application/pdf", settings)
    validated = validation.recompute_totals(extracted)

    vendor_hist = history.get_vendor_history(extracted.vendor_name, sheets_client)
    category_hist = history.get_category_history(extracted.category, sheets_client)
    all_records = sheets_client.get_all_records()

    flags, is_flagged = anomaly.check_anomalies(
        extracted, validated, vendor_hist, category_hist, all_records, settings
    )
    assert is_flagged is True

    record = ledger.write_ledger_record(
        extracted, validated, "Flagged", [f.reason for f in flags], sheets_client
    )

    assert record.status == "Flagged"
    assert record.total == validated.recomputed_total  # never the raw broken total
    assert len(record.flag_reasons) >= 2


def test_resolve_flag_updates_status(sheets_client, sample_extraction):
    validated = validation.recompute_totals(sample_extraction)
    record = ledger.write_ledger_record(
        sample_extraction, validated, "Flagged", ["some reason"], sheets_client
    )

    resolved = ledger.resolve_flag(record.id, "reviewer@example.com", sheets_client)

    assert resolved is not None
    assert resolved.status == "Resolved"
    assert resolved.reviewed_by == "reviewer@example.com"
    assert resolved.reviewed_date == dt.date.today()


def test_unsupported_file_type_rejected(settings):
    from fastapi import HTTPException

    try:
        extraction.extract_invoice(b"not a real file", "text/plain", settings)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 400
