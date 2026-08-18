"""recompute_totals(): never trust the model's math -- recompute it in code.

Per line item: amount should equal quantity * unit_price.
subtotal should equal the sum of line item amounts.
total should equal subtotal + tax.

Mismatches beyond a small tolerance don't reject the invoice outright -- they
become a `math_mismatch` signal fed into anomaly detection (services/anomaly.py),
and the ledger always stores the *recomputed* canonical totals, never the raw
extracted ones.
"""

from app.models.invoice import InvoiceExtraction, ValidationResult

TOLERANCE = 0.01


def recompute_totals(extraction: InvoiceExtraction) -> ValidationResult:
    discrepancies: list[str] = []

    for idx, item in enumerate(extraction.line_items, start=1):
        expected_amount = round(item.quantity * item.unit_price, 2)
        if abs(expected_amount - item.amount) > TOLERANCE:
            discrepancies.append(
                f"Line item {idx} ('{item.description}'): amount {item.amount:.2f} "
                f"does not match quantity * unit_price ({expected_amount:.2f})"
            )

    recomputed_subtotal = round(sum(item.amount for item in extraction.line_items), 2)
    if abs(recomputed_subtotal - extraction.subtotal) > TOLERANCE:
        discrepancies.append(
            f"Subtotal {extraction.subtotal:.2f} does not match sum of line items "
            f"({recomputed_subtotal:.2f})"
        )

    recomputed_total = round(recomputed_subtotal + extraction.tax, 2)
    if abs(recomputed_total - extraction.total) > TOLERANCE:
        discrepancies.append(
            f"Total {extraction.total:.2f} does not match subtotal + tax "
            f"({recomputed_total:.2f})"
        )

    return ValidationResult(
        recomputed_subtotal=recomputed_subtotal,
        recomputed_total=recomputed_total,
        discrepancies=discrepancies,
        math_mismatch=len(discrepancies) > 0,
    )
