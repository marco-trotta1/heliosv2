from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from helios.api.routes import router
from helios.api.runtime import build_runtime
from helios.config import Settings, get_settings
from helios.schemas.outputs import ErrorResponse


logger = logging.getLogger(__name__)

def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, resolved_settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = build_runtime(resolved_settings)
        app.state.settings = resolved_settings
        app.state.runtime = runtime
        app.state.rate_limiter = runtime.rate_limiter
        yield

    app = FastAPI(
        title=resolved_settings.app_name,
        description="Helios is an irrigation decision-support prototype for local evaluation and demos.",
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        issues = [err["msg"] for err in exc.errors()]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=ErrorResponse(
                error_code="validation_error",
                detail="Request validation failed. Check the field values and try again.",
                issues=issues,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        error_code = {
            400: "bad_request",
            404: "not_found",
            429: "rate_limited",
            503: "service_unavailable",
        }.get(exc.status_code, "request_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error_code=error_code, detail=detail).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled Helios API error", extra={"path": request.url.path})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code="internal_error",
                detail="Helios hit an internal error. Review the server logs before retrying.",
            ).model_dump(mode="json"),
        )

    app.include_router(router)
    return app


app = create_app()
