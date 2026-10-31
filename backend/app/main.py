import asyncio
import logging
import secrets
from functools import partial
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import errors
from .config import Settings, load_settings
from .engine import Engine, load_engine
from .errors import AppError
from .inputs import ANALYZE_BODY, read_input
from .insights import build_stats
from .pipeline import analyze_text
from .schemas import AnalyzeResponse, ErrorResponse, HealthResponse, OriginRequest, StatsResponse
from .stats import StatsStore, open_store

log = logging.getLogger("scamguard")


def create_app(
    settings: Optional[Settings] = None, engine: Optional[Engine] = None, store: Optional[StatsStore] = None
) -> FastAPI:
    settings = settings or load_settings()
    engine = engine or load_engine(settings.model_dir, settings.require_model)
    store = store or open_store(settings.database_url)

    # Access logs never hold bodies, but they are off anyway: nothing about a request is logged.
    logging.getLogger("uvicorn.access").disabled = True

    app = FastAPI(title="ScamGuard API")
    app.state.engine = engine
    app.state.settings = settings
    app.state.store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, _exc: RequestValidationError):
        # FastAPI's default 422 echoes the input back, so it is replaced.
        return JSONResponse({"detail": errors.INVALID}, status_code=422)

    @app.get("/health", response_model=HealthResponse)
    def health():
        return HealthResponse(status="ok", model_version=engine.model_version, mock=engine.mock)

    @app.post(
        "/analyze",
        response_model=AnalyzeResponse,
        responses={code: {"model": ErrorResponse} for code in (400, 413, 415, 422, 500, 504)},
        openapi_extra=ANALYZE_BODY,
    )
    async def analyze(request: Request):
        raw, source = await read_input(request)
        try:
            loop = asyncio.get_running_loop()
            work = loop.run_in_executor(None, partial(analyze_text, raw, source, engine))
            result = await asyncio.wait_for(work, timeout=settings.timeout_seconds)
        except AppError:
            raise
        except TimeoutError:
            # The worker thread finishes on its own; its result is dropped.
            raise AppError(504, errors.TIMEOUT) from None
        except Exception as exc:
            # Only the type is logged: messages and tracebacks can carry chat text.
            log.error("analyze failed: %s", type(exc).__name__)
            raise AppError(500, errors.INTERNAL) from None
        try:
            record_id = await loop.run_in_executor(None, store.record, result.verdict, source)
        except Exception as exc:
            # The verdict is still returned; only this check goes uncounted.
            log.error("stats record failed: %s", type(exc).__name__)
            return result
        return result.model_copy(update={"record_id": record_id})

    @app.post(
        "/checks/{record_id}/origin",
        status_code=204,
        responses={code: {"model": ErrorResponse} for code in (404, 409, 422, 500)},
    )
    def set_origin(record_id: str, body: OriginRequest):
        try:
            outcome = store.set_origin(record_id, body.origin)
        except Exception as exc:
            log.error("stats origin failed: %s", type(exc).__name__)
            raise AppError(500, errors.INTERNAL) from None
        if outcome == "missing":
            raise AppError(404, errors.CHECK_NOT_FOUND)
        if outcome == "not_allowed":
            raise AppError(409, errors.ORIGIN_NOT_ALLOWED)
        return Response(status_code=204)

    @app.get(
        "/stats",
        response_model=StatsResponse,
        responses={code: {"model": ErrorResponse} for code in (401, 404, 503)},
    )
    def stats(request: Request):
        if not settings.admin_token:
            raise AppError(404, errors.NOT_ALLOWED)
        given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not secrets.compare_digest(given.encode(), settings.admin_token.encode()):
            raise AppError(401, errors.NOT_ALLOWED)
        try:
            rows = store.counts()
        except Exception as exc:
            log.error("stats read failed: %s", type(exc).__name__)
            raise AppError(503, errors.STATS_UNAVAILABLE) from None
        return build_stats(rows)

    return app


app = create_app()
