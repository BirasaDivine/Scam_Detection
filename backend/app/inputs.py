"""Reads the chat from a request: JSON text or a .txt upload, under the size caps."""

import codecs

from fastapi import Request
from pydantic import TypeAdapter, ValidationError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartParser

from . import errors
from .config import MAX_BODY_BYTES, MAX_FILE_BYTES
from .errors import AppError
from .schemas import Source, TextRequest

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


async def read_input(request: Request) -> tuple[str, Source]:
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
