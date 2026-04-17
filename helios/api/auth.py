from __future__ import annotations

from secrets import compare_digest
from typing import Final

from fastapi import HTTPException, Request, status

from helios.config import get_settings

BEARER_PREFIX: Final = "Bearer "
AUTH_FAILURE_DETAIL: Final = "Invalid or missing API key."


def _raise_invalid_api_key() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=AUTH_FAILURE_DETAIL,
    )


def verify_api_key(request: Request) -> None:
    """Reject requests without a valid bearer token when prototype auth is enabled."""
    settings = get_settings()
    configured_key = settings.api_key.strip()
    if configured_key == "":
        return

    auth_header = request.headers.get("Authorization") or ""
    scheme, _, provided_key = auth_header.partition(" ")
    if scheme != "Bearer" or not provided_key:
        _raise_invalid_api_key()

    if not compare_digest(provided_key, configured_key):
        _raise_invalid_api_key()
