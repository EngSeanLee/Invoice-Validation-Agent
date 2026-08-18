"""POST /api/invoices -- the core agent loop from the spec:
receive file -> extract -> validate/recompute -> check anomalies -> write ledger.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.dependencies import get_sheets_client
from app.models.invoice import ProcessInvoiceResult
from app.services import anomaly, extraction, history, ledger, validation
from app.services.sheets_client import SheetsClient

router = APIRouter()


@router.post("/api/invoices", response_model=ProcessInvoiceResult)
async def process_invoice(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    sheets_client: SheetsClient = Depends(get_sheets_client),
) -> ProcessInvoiceResult:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    extracted = extraction.extract_invoice(file_bytes, file.content_type or "", settings)
    validated = validation.recompute_totals(extracted)

    vendor_hist = history.get_vendor_history(extracted.vendor_name, sheets_client)
    category_hist = history.get_category_history(
        extracted.category or "Uncategorized", sheets_client
    )
    all_records = sheets_client.get_all_records()

    flags, is_flagged = anomaly.check_anomalies(
        extracted, validated, vendor_hist, category_hist, all_records, settings
    )
    status = "Flagged" if is_flagged else "Clean"
    flag_reasons = [f.reason for f in flags] if is_flagged else []

    record = ledger.write_ledger_record(
        extracted, validated, status, flag_reasons, sheets_client
    )

    return ProcessInvoiceResult(
        invoice_id=record.id,
        extraction=extracted,
        validation=validated,
        status=status,
        flag_reasons=flag_reasons,
    )
