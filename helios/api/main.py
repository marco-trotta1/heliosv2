from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

import fastapi
from fastapi import status
from fastapi.exceptions import RequestValidationError as ValidationError
from fastapi.middleware.cors import CORSMiddleware as CorsMiddleware
from fastapi.responses import JSONResponse as JsonResponse
from starlette.middleware.base import BaseHTTPMiddleware as HTTPMiddleware

from helios.api.routes import router
from helios.api.runtime import build_runtime
from helios.config import Settings, get_settings
from helios.schemas.outputs import ErrorResponse


logger = logging.getLogger("helios.api")


def _configure_logging(settings: Settings) -> None:
    log_level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _warning_if_cors_is_open(settings: Settings) -> None:
    if "*" in settings.cors_allowed_origins:
        logger.warning("Wildcard CORS is enabled. Set HELIOS_CORS_ALLOW_ORIGINS before production use.")


def _http_error_code(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "unauthorized"
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    if status_code == 503:
        return "service_unavailable"
    return "request_error"


def _error_response(status_code: int, *, error_code: str, detail: str, issues: list[str] | None = None) -> JsonResponse:
    payload: dict[str, Any] = {
        "error_code": error_code,
        "detail": detail,
    }
    if issues:
        payload["issues"] = issues
    return JsonResponse(status_code=status_code, content=ErrorResponse(**payload).model_dump(mode="json"))


class RequestIdMiddleware(HTTPMiddleware):
    async def dispatch(self, request: fastapi.Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


def _attach_runtime_state(app: fastapi.FastAPI, resolved_settings: Settings) -> None:
    runtime = build_runtime(resolved_settings)
    app.state.runtime = runtime
    app.state.settings = resolved_settings
    app.state.rate_limiter = runtime.rate_limiter


def create_app(settings: Settings | None = None) -> fastapi.FastAPI:
    resolved_settings = settings or get_settings()
    _configure_logging(resolved_settings)
    _warning_if_cors_is_open(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: fastapi.FastAPI):
        _attach_runtime_state(app, resolved_settings)
        yield

    app = fastapi.FastAPI(
        title=resolved_settings.app_name,
        description="Helios is an irrigation decision-support prototype for local evaluation and demos.",
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CorsMiddleware,
        allow_origins=[*resolved_settings.cors_allowed_origins],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(_: fastapi.Request, exc: ValidationError) -> JsonResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="validation_error",
            detail="Request validation failed. Check the field values and try again.",
            issues=[err["msg"] for err in exc.errors()],
        )

    @app.exception_handler(fastapi.HTTPException)
    async def http_exception_handler(_: fastapi.Request, exc: fastapi.HTTPException) -> JsonResponse:
        error_code = _http_error_code(exc.status_code)
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return _error_response(exc.status_code, error_code=error_code, detail=detail)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: fastapi.Request, exc: Exception) -> JsonResponse:
        logger.exception("Unhandled Helios API error", extra={"path": request.url.path, "error": repr(exc)})
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="internal_error",
            detail="Helios hit an internal error. Review the server logs before retrying.",
        )

    app.include_router(router)
    return app


app = create_app()
