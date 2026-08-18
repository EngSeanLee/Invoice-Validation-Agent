"""Pydantic models for the extracted-invoice pipeline (extraction -> validation -> anomaly)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceExtraction(BaseModel):
    """Structured shape the model is asked to return via client.messages.parse().

    This is exactly the extraction schema from the spec. Values here are what the
    model *claims* -- they are never trusted directly; see services/validation.py.
    """

    vendor_name: str
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float
    tax: float
    total: float
    category: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of recomputing totals in code -- never trust extracted math blindly."""

    recomputed_subtotal: float
    recomputed_total: float
    discrepancies: list[str] = Field(default_factory=list)
    math_mismatch: bool = False


class AnomalyFlag(BaseModel):
    """One triggered anomaly signal."""

    signal: str
    reason: str
    weight: int


class ProcessInvoiceResult(BaseModel):
    """Response shape for POST /api/invoices."""

    invoice_id: str
    extraction: InvoiceExtraction
    validation: ValidationResult
    status: str  # "Clean" | "Flagged"
    flag_reasons: list[str] = Field(default_factory=list)
