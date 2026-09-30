import json
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from src.api.deps import client_ip, get_container_from_request
from src.api.schemas import ErrorResponse, TraceOptionsBody, TraceResponse
from src.core.exceptions import InvalidConfig

router = APIRouter(prefix="/api", tags=["icons"])


@router.post(
    "/icons/trace",
    response_model=TraceResponse,
    responses={
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def trace(
    request: Request,
    file: Annotated[UploadFile, File()],
    options: Annotated[str | None, Form(description="JSON TraceOptions")] = None,
) -> TraceResponse:
    """Trace an uploaded PNG, JPEG or SVG into icon geometry. Stateless: nothing is stored."""
    try:
        parsed = TraceOptionsBody.model_validate(json.loads(options) if options else {})
    except (ValueError, ValidationError) as exc:
        raise InvalidConfig(
            "invalid trace options",
            [{"loc": ["options"], "msg": str(exc), "code": "invalid_options"}],
        ) from exc
    container = get_container_from_request(request)
    data = await file.read()
    service = container.icon_service()
    with container.client_limiter().slot(client_ip(request), "preview"):
        # Tracing is CPU work: keep it off the event loop.
        result = await run_in_threadpool(
            service.trace, data, file.filename or "upload", parsed, parsed.embed_source
        )
    return TraceResponse(**vars(result))
