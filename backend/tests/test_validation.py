import copy

from app.services.validation import recompute_totals


def test_clean_invoice_has_no_discrepancies(sample_extraction):
    result = recompute_totals(sample_extraction)
    assert result.math_mismatch is False
    assert result.discrepancies == []
    assert result.recomputed_subtotal == 125.0
    assert result.recomputed_total == 135.0


def test_line_item_amount_mismatch_detected(sample_extraction):
    bad = copy.deepcopy(sample_extraction)
    bad.line_items[0].amount = 999.0  # should be 100.0 (2 * 50.0)

    result = recompute_totals(bad)

    assert result.math_mismatch is True
    assert any("Line item 1" in d for d in result.discrepancies)


def test_subtotal_mismatch_detected(sample_extraction):
    bad = copy.deepcopy(sample_extraction)
    bad.subtotal = 500.0  # doesn't match sum of line items (125.0)

    result = recompute_totals(bad)

    assert result.math_mismatch is True
    assert any("Subtotal" in d for d in result.discrepancies)
    # recomputed value is what actually gets written to the ledger
    assert result.recomputed_subtotal == 125.0


def test_total_mismatch_detected(sample_extraction):
    bad = copy.deepcopy(sample_extraction)
    bad.total = 1000.0  # doesn't match subtotal + tax (135.0)

    result = recompute_totals(bad)

    assert result.math_mismatch is True
    assert any("Total" in d for d in result.discrepancies)
    assert result.recomputed_total == 135.0


def test_tolerance_absorbs_rounding_noise(sample_extraction):
    bad = copy.deepcopy(sample_extraction)
    bad.total = 135.005  # within the $0.01 tolerance

    result = recompute_totals(bad)

    assert result.math_mismatch is False
