from __future__ import annotations

from fastapi import HTTPException, Request, status

from helios.config import get_settings


def verify_api_key(request: Request) -> None:
    """FastAPI dependency that enforces Bearer token auth when HELIOS_API_KEY is set.

    When HELIOS_API_KEY is empty or unset, this dependency is a no-op (prototype mode).
    Only POST endpoints require auth; GET endpoints remain public.
    """
    settings = get_settings()
    expected_key = settings.api_key
    if not expected_key:
        return  # Auth disabled — prototype / demo mode

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    provided_key = auth_header[len("Bearer "):]
    if provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
