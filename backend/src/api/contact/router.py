from fastapi import APIRouter, Request

from src.api.deps import get_container_from_request
from src.api.schemas import ErrorResponse
from src.core.services.contact_service import ContactRequest

router = APIRouter(prefix="/api", tags=["contact"])


@router.post(
    "/contact",
    status_code=202,
    responses={422: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def contact(body: ContactRequest, request: Request) -> dict:
    """ "Don't have a printer?": send one email to the site owner (decision D19)."""
    get_container_from_request(request).contact_service().send(body)
    return {}
