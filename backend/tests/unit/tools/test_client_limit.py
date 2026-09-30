import pytest

from src.core.exceptions import RateLimited
from src.core.tools.client_limit import ClientConcurrencyLimiter


def test_caps_concurrent_requests_per_client_and_kind() -> None:
    limiter = ClientConcurrencyLimiter({"export": 1, "preview": 2})
    with limiter.slot("a", "export"):
        with pytest.raises(RateLimited), limiter.slot("a", "export"):
            pass
        with (
            limiter.slot("b", "export"),
            limiter.slot("a", "preview"),
            limiter.slot("a", "preview"),
            pytest.raises(RateLimited),
            limiter.slot("a", "preview"),
        ):
            pass
    with limiter.slot("a", "export"):
        pass
    assert not limiter._active


def test_releases_the_slot_when_the_request_fails() -> None:
    limiter = ClientConcurrencyLimiter({"export": 1})
    with pytest.raises(ValueError), limiter.slot("a", "export"):
        raise ValueError
    with limiter.slot("a", "export"):
        pass
