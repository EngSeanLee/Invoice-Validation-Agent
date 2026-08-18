"""FastAPI entrypoint. Config is validated eagerly (see app/config.py) so a
missing ANTHROPIC_API_KEY / GOOGLE_SERVICE_ACCOUNT_JSON / SHEET_ID fails fast
with a clear message instead of an obscure error on the first request.

The Google Sheets connection is built lazily on first use (see
dependencies.get_sheets_client), not at app startup -- this works the same way
under a long-lived local `uvicorn` process and under a serverless host (e.g.
Vercel) where each cold-started instance handles its own first request without
relying on a startup/lifespan hook.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, invoices, ledger

settings = get_settings()  # fails fast (SystemExit) if required env vars are missing

app = FastAPI(title="Invoice Validation Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(ledger.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
