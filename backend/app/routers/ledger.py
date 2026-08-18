"""GET /api/ledger, POST /api/ledger/{invoice_id}/resolve"""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_sheets_client
from app.models.ledger import LedgerRecord, ResolveRequest
from app.services import ledger as ledger_service
from app.services.sheets_client import SheetsClient

router = APIRouter()


@router.get("/api/ledger")
def get_ledger(sheets_client: SheetsClient = Depends(get_sheets_client)) -> dict:
    records = ledger_service.get_ledger(sheets_client)
    return {"records": records}


@router.post("/api/ledger/{invoice_id}/resolve", response_model=LedgerRecord)
def resolve(
    invoice_id: str,
    body: ResolveRequest,
    sheets_client: SheetsClient = Depends(get_sheets_client),
) -> LedgerRecord:
    record = ledger_service.resolve_flag(invoice_id, body.reviewer, sheets_client)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"No ledger record found with id '{invoice_id}'"
        )
    return record
