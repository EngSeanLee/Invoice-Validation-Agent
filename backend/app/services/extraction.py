"""extract_invoice(): Claude vision -> structured InvoiceExtraction.

Uses client.messages.parse(..., output_format=InvoiceExtraction) so the SDK
validates the response against the Pydantic schema for us -- no manual JSON
parsing/repair. The raw model output is still never trusted for math; see
services/validation.py for the recompute step that runs right after this.
"""

import base64

import anthropic
from fastapi import HTTPException

from app.config import Settings
from app.models.invoice import InvoiceExtraction

SUPPORTED_MEDIA_TYPES = {
    "application/pdf": "document",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
}

EXTRACTION_INSTRUCTIONS = """\
You are extracting structured data from a vendor invoice (PDF or photo/scan of \
an invoice). Read the document carefully and return the invoice's data.

Rules:
- vendor_name: the company that ISSUED the invoice (billing FROM), not the recipient.
- invoice_number: the invoice's own identifier as printed. If truly absent, use \
"UNKNOWN".
- invoice_date: the invoice's issue date, ISO 8601 (YYYY-MM-DD).
- due_date: payment due date if printed, else null.
- line_items: every billable line, with quantity, unit_price, and amount as \
printed (do not recompute here -- just transcribe what's on the document).
- subtotal, tax, total: transcribe the printed values exactly, even if they \
look inconsistent with the line items -- downstream validation handles that.
- category: infer a short spend category (e.g. "Software", "Office Supplies", \
"Travel", "Utilities", "Professional Services", "Marketing") from the vendor \
and line items if no category is explicitly printed on the invoice.
"""


def _client(settings: Settings) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def extract_invoice(
    file_bytes: bytes, mime_type: str, settings: Settings
) -> InvoiceExtraction:
    """Call Claude's vision/document understanding to extract structured invoice data.

    Raises HTTPException (4xx/5xx) on any Claude API failure, mapped from the
    SDK's typed exception hierarchy so the frontend gets a clean error instead
    of a raw traceback.
    """
    block_type = SUPPORTED_MEDIA_TYPES.get(mime_type)
    if block_type is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{mime_type}'. Supported: "
                f"{', '.join(SUPPORTED_MEDIA_TYPES)}"
            ),
        )

    encoded = base64.standard_b64encode(file_bytes).decode("utf-8")
    file_block = {
        "type": block_type,
        "source": {"type": "base64", "media_type": mime_type, "data": encoded},
    }

    client = _client(settings)
    try:
        response = client.messages.parse(
            model=settings.claude_model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [file_block, {"type": "text", "text": EXTRACTION_INSTRUCTIONS}],
                }
            ],
            output_format=InvoiceExtraction,
        )
    except anthropic.AuthenticationError as exc:
        raise HTTPException(
            status_code=502, detail="Claude API authentication failed -- check ANTHROPIC_API_KEY."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=429, detail="Claude API rate limit hit. Try again shortly."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Claude API error ({exc.status_code}): {exc.message}"
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(
            status_code=502, detail="Could not reach the Claude API. Check network connectivity."
        ) from exc

    return response.parsed_output
