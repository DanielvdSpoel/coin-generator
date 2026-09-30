import ipaddress
from functools import lru_cache

from fastapi import Request

from src.container import Container


def get_container_from_request(request: Request) -> Container:
    return request.state.container


@lru_cache(maxsize=8)
def _networks(cidrs: tuple[str, ...]) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(ipaddress.ip_network(c, strict=False) for c in cidrs)


def _parse(ip: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(ip)
    except ValueError:
        return None


def client_ip(request: Request) -> str:
    """The visitor's IP, for per-client limits.

    ``X-Forwarded-For`` is read from the right, skipping addresses of trusted
    proxies (``settings.trusted_proxies``: the cluster's private ranges and, in
    prod, Cloudflare's). The first address that is not a proxy is the visitor.
    Reading from the left would trust whatever the client put there: Cloudflare
    appends to an incoming header rather than replacing it.
    """
    networks = _networks(tuple(request.state.container.settings.trusted_proxies))
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    peer = request.client.host if request.client else ""
    if peer:
        hops.append(peer)
    for hop in reversed(hops):
        address = _parse(hop)
        # Not an address (garbage, or the test client's "testclient"): skip it.
        if address is not None and not any(address in n for n in networks):
            return hop
    return hops[0] if hops else "unknown"
