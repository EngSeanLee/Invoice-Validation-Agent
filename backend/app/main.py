"""FastAPI entrypoint. Config is validated eagerly (see app/config.py) so a
missing ANTHROPIC_API_KEY / GOOGLE_SERVICE_ACCOUNT_JSON / SHEET_ID fails fast
with a clear message instead of an obscure error on the first request. The
Google Sheets connection itself is verified at startup (lifespan), before the
app starts serving traffic.
"""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import invoices, ledger
from app.services.sheets_client import GoogleSheetsClient

settings = get_settings()  # fails fast (SystemExit) if required env vars are missing


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        service_account_info = settings.resolve_service_account_info()
        sheets_client = GoogleSheetsClient(settings.sheet_id, service_account_info)
        sheets_client.ensure_headers()
    except Exception as exc:
        print(
            f"\nFailed to connect to the Google Sheets ledger: {exc}\n"
            "Check GOOGLE_SERVICE_ACCOUNT_JSON and SHEET_ID, and confirm the "
            "target Sheet is shared with the service account's client_email as "
            "Editor. See the README's 'Google Cloud service account setup' section.\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    app.state.sheets_client = sheets_client
    yield


app = FastAPI(title="Invoice Validation Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(invoices.router)
app.include_router(ledger.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
