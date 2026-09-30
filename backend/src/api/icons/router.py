import json
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import ValidationError

from src.api.deps import get_container_from_request
from src.api.schemas import ErrorResponse, TraceOptionsBody, TraceResponse
from src.core.exceptions import InvalidConfig

router = APIRouter(prefix="/api", tags=["icons"])


@router.post(
    "/icons/trace",
    response_model=TraceResponse,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def trace(
    request: Request,
    file: Annotated[UploadFile, File()],
    options: Annotated[str | None, Form(description="JSON TraceOptions")] = None,
) -> TraceResponse:
    """Trace an uploaded PNG or JPEG into icon geometry. Stateless: nothing is stored."""
    try:
        parsed = TraceOptionsBody.model_validate(json.loads(options) if options else {})
    except (ValueError, ValidationError) as exc:
        raise InvalidConfig(
            "invalid trace options",
            [{"loc": ["options"], "msg": str(exc), "code": "invalid_options"}],
        ) from exc
    container = get_container_from_request(request)
    data = await file.read()
    result = container.icon_service().trace(
        data, file.filename or "upload", parsed, embed_source=parsed.embed_source
    )
    return TraceResponse(**vars(result))
