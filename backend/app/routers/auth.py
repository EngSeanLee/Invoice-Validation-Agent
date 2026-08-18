"""POST /api/auth/check -- validates a candidate passphrase for the optional
shared-passphrase gate (see dependencies.require_passphrase). This endpoint
itself is never gated: the frontend needs to be able to ask "is a passphrase
even required?" before a user has entered one, and "is this one right?" as
they type it.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import Settings, get_settings

router = APIRouter()


class AuthCheckRequest(BaseModel):
    passphrase: str = ""


class AuthCheckResponse(BaseModel):
    required: bool


@router.post("/api/auth/check", response_model=AuthCheckResponse)
def check_passphrase(body: AuthCheckRequest) -> AuthCheckResponse:
    settings: Settings = get_settings()
    if not settings.app_passphrase:
        return AuthCheckResponse(required=False)
    if body.passphrase != settings.app_passphrase:
        raise HTTPException(status_code=401, detail="Incorrect passphrase.")
    return AuthCheckResponse(required=True)
