"""Domain exceptions → HTTP, in one place.

Every error body has the same shape: ``{"detail": [{"loc", "msg", "code"}]}``.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.exceptions import (
    BuildTimeout,
    IconTraceFailed,
    InvalidConfig,
    InvalidFont,
    MailerError,
    NotWatertight,
    PayloadTooLarge,
)

logger = logging.getLogger(__name__)


def error_response(status: int, code: str, msg: str, loc: list | None = None, **headers: str):
    return JSONResponse(
        status_code=status,
        content={"detail": [{"loc": loc or [], "msg": msg, "code": code}]},
        headers=headers or None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _request_validation(request: Request, exc: RequestValidationError):
        detail = [
            {"loc": list(error["loc"]), "msg": error["msg"], "code": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": detail})

    @app.exception_handler(InvalidConfig)
    async def _invalid_config(request: Request, exc: InvalidConfig):
        return JSONResponse(status_code=422, content={"detail": exc.errors})

    @app.exception_handler(InvalidFont)
    async def _invalid_font(request: Request, exc: InvalidFont):
        return error_response(422, "invalid_font", str(exc), ["font"])

    @app.exception_handler(IconTraceFailed)
    async def _trace_failed(request: Request, exc: IconTraceFailed):
        return error_response(422, "trace_failed", str(exc), ["file"])

    @app.exception_handler(PayloadTooLarge)
    async def _too_large(request: Request, exc: PayloadTooLarge):
        return error_response(413, "payload_too_large", str(exc))

    @app.exception_handler(BuildTimeout)
    async def _timeout(request: Request, exc: BuildTimeout):
        logger.warning("build timeout on %s: %s", request.url.path, exc)
        return error_response(503, "build_timeout", str(exc), **{"Retry-After": "5"})

    @app.exception_handler(NotWatertight)
    async def _not_watertight(request: Request, exc: NotWatertight):
        logger.error("not watertight on %s: %s", request.url.path, exc)
        return error_response(500, "not_watertight", str(exc))

    @app.exception_handler(MailerError)
    async def _mailer(request: Request, exc: MailerError):
        logger.error("mail failed: %s", exc)
        return error_response(502, "mail_failed", "The message could not be sent. Try again later.")
