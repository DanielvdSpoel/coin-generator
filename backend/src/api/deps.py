from fastapi import Request

from src.container import Container


def get_container_from_request(request: Request) -> Container:
    return request.state.container


def client_ip(request: Request) -> str:
    """The visitor's IP, for per-client limits.

    In the cluster Traefik trusts ``X-Forwarded-For`` only from Cloudflare's
    ranges and rewrites it for everyone else, so its leftmost entry is the
    visitor. Locally there is no proxy and the socket peer is the client.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    first = forwarded.split(",", 1)[0].strip()
    if first:
        return first
    return request.client.host if request.client else "unknown"
