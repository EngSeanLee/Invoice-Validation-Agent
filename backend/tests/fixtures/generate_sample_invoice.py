"""Builds a small synthetic invoice PDF at test time, used as smoke-test
input for the extraction pipeline. Not real vendor data."""

from fpdf import FPDF
from fpdf.enums import XPos, YPos


def build_sample_invoice_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, "Acme Testing Co", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, "Invoice #: ACME-0001", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Date: 2026-06-01", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Due Date: 2026-06-30", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.cell(0, 8, "Widget A  x2 @ $50.00 = $100.00", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Widget B  x1 @ $25.00 = $25.00", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.cell(0, 8, "Subtotal: $125.00", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Tax: $10.00", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, "Total: $135.00", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())
