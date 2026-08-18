# Invoice Validation Agent

**Live demo:** [invoice-validation-agent.vercel.app](https://invoice-validation-agent.vercel.app) — passphrase-protected (ask the repo owner for it). The demo makes real Claude API calls and writes to a real Google Sheet, so it's gated to keep usage in check; see [Deployment](#deployment) for how it's hosted.

An agent that ingests vendor invoices (PDF or photo), extracts structured
data with Claude's vision capability, validates the extracted math in code,
flags anomalies using **combined statistical signals** (not a single rule),
and maintains a running ledger in Google Sheets that a reviewer can approve
or resolve directly from the app.

Built as a portfolio piece demonstrating real tool-use/agentic patterns —
structured extraction, code-side validation, an explainable rule-based
anomaly module, and a human-in-the-loop review step — rather than a plain
chat interface.

> **Synthetic data disclaimer:** with no real invoice history on day one,
> this project seeds the ledger with **synthetic, generated sample invoices**
> (`backend/app/seed/`) so the anomaly logic has a realistic baseline to
> compare against from the first real invoice. Every synthetic row is
> labeled `Source = Synthetic` in the Sheet and called out in the UI — it is
> not real company spend.

## Architecture

```
frontend/  React + Vite + TypeScript SPA (Upload view, Ledger view)
    │  fetch()
    ▼
backend/   FastAPI service
    │  POST /api/invoices        (extract → validate → check anomalies → write ledger)
    │  GET  /api/ledger          (read current ledger state)
    │  POST /api/ledger/{id}/resolve   (mark a flagged item resolved)
    │
    ├─ Claude API (vision + structured JSON output) — extraction
    └─ Google Sheets API (service account) — ledger datastore
```

Each invoice is processed **synchronously**: the Claude vision call takes a
few seconds, and FastAPI/uvicorn handles several concurrent in-flight
requests fine at this scale. Batch upload is just N single-invoice calls,
concurrency-limited client-side — no job queue/polling infrastructure was
worth building for a demo-scale tool. (See Roadmap below for the future
alternative if volume grows.)

## Out of scope for v1

- Expense receipts / purchase orders (architecture allows extending later)
- Email-forwarding intake
- Automated "necessity" judgment — the agent flags, a human decides
- Multi-user auth/permissions (single-user/demo scope — see Roadmap)

## Prerequisites

- Python 3.11+ and Node.js 20+
- An [Anthropic API key](https://console.anthropic.com/settings/keys)
- A Google Cloud project (free tier is fine) for the Sheets service account

## Setup

### 1. Google Cloud service account + Sheet

The ledger is a Google Sheet, written to via a service account (not your
personal Google login), so the backend can read/write it headlessly.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and
   create a new project (or select an existing one).
2. In **APIs & Services → Library**, search for **Google Sheets API** and
   click **Enable**.
3. In **APIs & Services → Credentials**, click **Create Credentials →
   Service account**. Give it any name (e.g. `invoice-agent`), skip the
   optional role grants, and click **Done**.
4. Open the new service account, go to the **Keys** tab, click **Add Key →
   Create new key → JSON**, and download it. This is your
   `GOOGLE_SERVICE_ACCOUNT_JSON` — treat it like a password (it's gitignored
   by default in this repo; never commit it).
5. Create a new Google Sheet (any name) — this will hold the ledger. Add a
   tab named exactly `Ledger` (the backend creates the header row on first
   run; you just need the tab to exist).
6. Copy the **Sheet ID** from its URL:
   `https://docs.google.com/spreadsheets/d/`**`<SHEET_ID>`**`/edit` — this is
   your `SHEET_ID`.
7. Open the downloaded JSON key and copy the `client_email` value. Back in
   the Google Sheet, click **Share** and share it with that email address as
   **Editor**.

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SERVICE_ACCOUNT_JSON=./service-account-key.json   # or paste the raw JSON
SHEET_ID=the-sheet-id-from-step-1.6
```

Save the downloaded key JSON as `backend/service-account-key.json` (already
gitignored), or set `GOOGLE_SERVICE_ACCOUNT_JSON` to a different path, or
paste the JSON content directly as the value.

Extraction defaults to **Claude Haiku 4.5** (`CLAUDE_MODEL`) — invoice
extraction is a well-specified structured-JSON task, not open-ended
reasoning, so the cheaper/faster model is the right fit; override to
`claude-sonnet-5` or `claude-opus-5` if you need higher accuracy on messy
scans. Leave `APP_PASSPHRASE` unset for local dev (no gate); set it to
require a passphrase before upload/ledger access — see
[Public access / passphrase gate](#public-access--passphrase-gate).

Seed the synthetic baseline data (run once, before your first real upload):

```bash
python -m app.seed.generate_synthetic_seed
```

Run the API:

```bash
uvicorn app.main:app --reload
```

The backend validates required env vars at startup and exits with a clear
error message (pointing back to this section) if anything is missing or the
Sheet isn't reachable — it won't fail silently on the first real request.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # defaults to http://localhost:8000, adjust if needed
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

## Usage

1. **Upload** tab — drag/select one or more invoice files (PDF, PNG, JPG,
   WEBP). Each is processed independently; watch per-file status update as
   extraction/validation/anomaly-check completes.
2. **Ledger** tab — see every processed invoice, Clean or Flagged. Click a
   Flagged row to see its specific flag reason(s) and mark it resolved
   (records your name and the date, and updates the ledger).

## Tests

```bash
cd backend
pytest
```

Tests run entirely against a `MockSheetsClient` (in-memory) and a
monkeypatched Anthropic client — the full extract → validate → anomaly →
ledger pipeline is exercised with **no live credentials required**.

## Public access / passphrase gate

There's no per-user auth in v1 (see Roadmap) — but a fully open deployment
would let anyone with the URL trigger real Claude API spend and write to
your real Sheet. `APP_PASSPHRASE` (backend env var) closes that gap cheaply:
when set, `POST /api/invoices`, `GET /api/ledger`, and the resolve endpoint
all require a matching `X-App-Passphrase` header (see
`backend/app/dependencies.py::require_passphrase`); `POST /api/auth/check` is
the one ungated endpoint, used by the frontend to validate a candidate
passphrase before storing it in `localStorage`. Leave `APP_PASSPHRASE` unset
for local dev to skip the gate entirely. This is a shared secret, not
per-user accounts — fine for a portfolio demo, not a substitute for real auth
if this ever became a multi-user internal tool.

## Deployment

The live demo runs on [Vercel](https://vercel.com) as two projects from this
same repo:

- **Backend** (`backend/` as root directory) — deployed via Vercel's native
  [FastAPI framework preset](https://vercel.com/docs/frameworks/backend/fastapi),
  which auto-detects `app/main.py`'s exported `app` and installs
  `requirements.txt`. No `api/` wrapper needed. `backend/vercel.json` sets
  `maxDuration` for the extraction endpoint (Claude + Sheets calls can take a
  few seconds). The Sheets client is built lazily on first request per
  serverless instance (see `dependencies.py`) rather than at a startup
  lifespan hook, so it behaves the same under a long-lived local `uvicorn`
  process and under fresh per-invocation serverless instances.
- **Frontend** (`frontend/` as root directory) — deployed as a static Vite
  build, `VITE_API_BASE_URL` pointed at the backend's production URL.

Required backend environment variables on Vercel (Project Settings →
Environment Variables): `ANTHROPIC_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON`
(paste the full JSON key content — there's no filesystem to point a path
at), `SHEET_ID`, `CORS_ALLOWED_ORIGINS` (the frontend's production URL), and
`APP_PASSPHRASE` if you want the demo gated. `CLAUDE_MODEL`,
`ANOMALY_ZSCORE_THRESHOLD`, and `ANOMALY_SIGNAL_THRESHOLD` are optional, same
as local dev.

## Anomaly detection

Signals are independent, swappable functions (`backend/app/services/anomaly.py`):

| Signal | Fires when | Weight |
|---|---|---|
| `amount_above_vendor_avg` | Total is `ANOMALY_ZSCORE_THRESHOLD` std. deviations above that vendor's historical average (needs ≥3 prior invoices) | 1 |
| `new_vendor` | Vendor has no prior invoices in the ledger | 1 |
| `duplicate_invoice` | Same vendor + invoice number, or same vendor + amount + date, already in the ledger | 2 (flags alone) |
| `category_trend` | This month's category spend is ≥1.5x the historical monthly average | 1 |
| `math_mismatch` | Recomputed totals don't match the extracted invoice's printed math | 1 |

Triggered signals' weights are summed and compared to
`ANOMALY_SIGNAL_THRESHOLD` (default 2) — this is what implements "combined
signals, not one rule alone," while still letting a high-confidence
duplicate invoice number flag on its own. Both thresholds are env-tunable
without touching code.

## Roadmap (beyond v1)

1. Extend the extraction schema/pipeline to receipts and purchase orders
2. Add email-forwarding intake
3. Replace the synthetic baseline with real historical data once available
4. Replace the shared-passphrase gate with real per-user auth if this is
   ever pitched as an internal tool
5. If invoice volume grows enough that synchronous processing becomes slow,
   move `POST /api/invoices` to a background-task + polling model instead of
   a request/response call

## License

MIT — see [LICENSE](LICENSE).
