import pytest

from src.core.exceptions import RateLimited
from src.core.tools.rate_limit import SlidingWindowLimiter


def test_limits_per_key_and_recovers_after_the_window() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_s=10)
    limiter.hit("a", now=0)
    limiter.hit("a", now=1)
    limiter.hit("b", now=1)
    with pytest.raises(RateLimited) as exc:
        limiter.hit("a", now=2)
    assert exc.value.retry_after_s == 9
    limiter.hit("a", now=10.5)


def test_prunes_idle_keys() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_s=1, max_keys=2)
    for i in range(5):
        limiter.hit(str(i), now=i * 2)
    assert len(limiter._hits) <= 3
