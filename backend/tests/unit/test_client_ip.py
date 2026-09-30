from types import SimpleNamespace

import pytest

from src.api.deps import client_ip
from src.settings import Settings

CLOUDFLARE = "104.16.0.0/13"


def _request(xff: str | None, peer: str = "10.0.3.4", extra: tuple[str, ...] = (CLOUDFLARE,)):
    settings = Settings(_env_file=None, environment="test")
    settings.trusted_proxies = [*settings.trusted_proxies, *extra]
    headers = {"x-forwarded-for": xff} if xff is not None else {}
    return SimpleNamespace(
        headers=headers,
        client=SimpleNamespace(host=peer),
        state=SimpleNamespace(container=SimpleNamespace(settings=settings)),
    )


@pytest.mark.parametrize(
    ("xff", "peer", "expected"),
    [
        # Through Cloudflare: visitor, then a Cloudflare edge; Traefik is the peer.
        ("203.0.113.5, 104.16.1.1", "10.0.3.4", "203.0.113.5"),
        # A forged left-hand entry is ignored.
        ("198.51.100.1, 203.0.113.5, 104.16.1.1", "10.0.3.4", "203.0.113.5"),
        # Garbage entries are skipped.
        ("not-an-ip, 203.0.113.5", "10.0.3.4", "203.0.113.5"),
        # Local development: no proxy, the socket peer is the visitor.
        (None, "203.0.113.9", "203.0.113.9"),
        # Only proxies seen: fall back to the leftmost.
        ("10.1.1.1", "10.0.3.4", "10.1.1.1"),
    ],
)
def test_client_ip_reads_from_the_right(xff, peer, expected) -> None:
    assert client_ip(_request(xff, peer)) == expected
