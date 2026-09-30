"""Request-level plumbing: DI, body size limit, access log with request ids."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.errors import error_response
from src.container import Container

logger = logging.getLogger("coin.access")


class DIMiddleware(BaseHTTPMiddleware):
    """Puts the container on ``request.state`` so handlers resolve services from it."""

    def __init__(self, app: FastAPI, container: Container) -> None:
        super().__init__(app)
        self.container = container

    async def dispatch(self, request: Request, call_next):
        request.state.container = self.container
        return await call_next(request)


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversized bodies up front by ``Content-Length``.

    JSON bodies carry icon polygons and embedded fonts, so their cap is separate
    from the multipart upload cap (decisions D14, D18).
    """

    def __init__(self, app: FastAPI, json_bytes: int, upload_bytes: int) -> None:
        super().__init__(app)
        self._json = json_bytes
        self._upload = upload_bytes

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit():
            content_type = request.headers.get("content-type", "")
            limit = self._upload if content_type.startswith("multipart/") else self._json
            if int(length) > limit:
                return error_response(
                    413, "payload_too_large", f"request body exceeds {limit // (1024 * 1024)} MB"
                )
        return await call_next(request)


class AccessLogMiddleware(BaseHTTPMiddleware):
    """One log line per request with a request id, echoed as ``X-Request-ID``."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1e3
        response.headers["X-Request-ID"] = request_id
        if not request.url.path.startswith("/api/health"):
            logger.info(
                "%s %s %s %.0fms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 1),
                },
            )
        return response
