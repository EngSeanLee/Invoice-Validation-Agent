import datetime as dt
import sys
from pathlib import Path

import pytest

# Allow `import app...` when pytest is run from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings_for_tests
from app.models.invoice import InvoiceExtraction, LineItem
from app.services.sheets_client import MockSheetsClient


@pytest.fixture
def settings():
    return get_settings_for_tests()


@pytest.fixture
def sheets_client():
    return MockSheetsClient()


@pytest.fixture
def sample_extraction() -> InvoiceExtraction:
    """A clean, internally-consistent extracted invoice (math checks out)."""
    return InvoiceExtraction(
        vendor_name="Acme Testing Co",
        invoice_number="ACME-0001",
        invoice_date=dt.date(2026, 6, 1),
        due_date=dt.date(2026, 6, 30),
        line_items=[
            LineItem(description="Widget A", quantity=2, unit_price=50.0, amount=100.0),
            LineItem(description="Widget B", quantity=1, unit_price=25.0, amount=25.0),
        ],
        subtotal=125.0,
        tax=10.0,
        total=135.0,
        category="Office Supplies",
    )
