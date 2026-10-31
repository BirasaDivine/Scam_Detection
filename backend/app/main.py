import asyncio
import codecs
import logging
import secrets
from functools import partial
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, ValidationError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser

from . import errors
from .config import MAX_BODY_BYTES, MAX_FILE_BYTES, Settings, load_settings
from .engine import Engine, load_engine
from .errors import AppError
from .insights import build_stats
from .pipeline import analyze_text
from .schemas import (
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
    OriginRequest,
    Source,
    StatsResponse,
    TextRequest,
)
from .stats import StatsStore

log = logging.getLogger("scamguard")

# Keep uploads in memory: Starlette would otherwise spill parts over 1 MB to a temp file.
MultiPartParser.spool_max_size = MAX_BODY_BYTES

ALLOWED_FILE_TYPES = {"", "text/plain", "application/octet-stream"}
KNOWN_FIELDS = {"text", "source", "file"}
_source_adapter = TypeAdapter(Source)

ANALYZE_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": TextRequest.model_json_schema()},
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file", "source"],
                    "properties": {
                        "file": {"type": "string", "format": "binary"},
                        "source": {"type": "string", "enum": ["whatsapp", "plain", "sms"]},
                    },
                }
            },
        },
    }
}


def create_app(
    settings: Optional[Settings] = None, engine: Optional[Engine] = None, store: Optional[StatsStore] = None
) -> FastAPI:
    settings = settings or load_settings()
    engine = engine or load_engine(settings.model_dir, settings.require_model)
    store = store or StatsStore(settings.database_url)

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
        raw, source = await _read_input(request)
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


async def _read_input(request: Request) -> tuple[str, Source]:
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type == "multipart/form-data":
        return await _read_upload(request)
    if content_type == "application/json":
        return await _read_json(request)
    raise AppError(415, errors.WRONG_CONTENT_TYPE)


async def _read_capped_body(request: Request, too_large: str) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise AppError(413, too_large)
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise AppError(413, too_large)
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_json(request: Request) -> tuple[str, Source]:
    body = await _read_capped_body(request, errors.TEXT_TOO_LARGE)
    try:
        payload = TextRequest.model_validate_json(body)
    except ValidationError as exc:
        if any(e["type"] == "json_invalid" for e in exc.errors()):
            raise AppError(400, errors.BAD_REQUEST_BODY) from None
        raise AppError(422, _invalid_message(exc)) from None
    if len(payload.text.encode("utf-8")) > MAX_FILE_BYTES:
        raise AppError(413, errors.TEXT_TOO_LARGE)
    return payload.text, payload.source


async def _read_upload(request: Request) -> tuple[str, Source]:
    # Read under the cap first, then let Starlette parse the bytes already held.
    request._body = await _read_capped_body(request, errors.FILE_TOO_LARGE)
    try:
        form = await request.form(max_files=1, max_fields=2)
    except Exception:
        raise AppError(400, errors.BAD_REQUEST_BODY) from None
    try:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise AppError(422, f"{errors.INVALID} Check: file.")
        try:
            source = _source_adapter.validate_python(form.get("source"))
        except ValidationError:
            raise AppError(422, f"{errors.INVALID} Check: source.") from None
        if not (upload.filename or "").lower().endswith(".txt"):
            raise AppError(415, errors.WRONG_FILE_TYPE)
        if (upload.content_type or "").split(";")[0].strip().lower() not in ALLOWED_FILE_TYPES:
            raise AppError(415, errors.WRONG_FILE_TYPE)
        data = await upload.read()
    finally:
        await form.close()
    if len(data) > MAX_FILE_BYTES:
        raise AppError(413, errors.FILE_TOO_LARGE)
    return _decode(data), source


def _decode(data: bytes) -> str:
    try:
        if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
            text = data.decode("utf-16")
        else:
            text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AppError(400, errors.UNREADABLE) from None
    if "\x00" in text:
        raise AppError(400, errors.UNREADABLE)
    return text


def _invalid_message(exc: ValidationError) -> str:
    # Only known field names are named. Unknown keys could be user content.
    fields = sorted({str(e["loc"][0]) for e in exc.errors() if e["loc"] and e["loc"][0] in KNOWN_FIELDS})
    return f"{errors.INVALID} Check: {', '.join(fields)}." if fields else errors.INVALID


app = create_app()
