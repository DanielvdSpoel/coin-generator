from src.adapters.lru_mesh_cache import LruMeshCache


def test_get_and_put_with_hit_and_miss_counts() -> None:
    cache = LruMeshCache(budget_bytes=100)
    assert cache.get("a") is None
    cache.put("a", "A", 10)
    assert cache.get("a") == "A"
    assert cache.stats() == {"entries": 1, "size_bytes": 10, "hits": 1, "misses": 1}


def test_least_recently_used_is_evicted_first() -> None:
    cache = LruMeshCache(budget_bytes=30)
    cache.put("a", "A", 10)
    cache.put("b", "B", 10)
    cache.put("c", "C", 10)
    assert cache.get("a") == "A"  # touch a, so b is now the oldest
    cache.put("d", "D", 10)
    assert cache.get("b") is None
    assert cache.get("a") == "A" and cache.get("c") == "C" and cache.get("d") == "D"
    assert cache.stats()["size_bytes"] == 30


def test_replacing_a_key_accounts_its_size_once() -> None:
    cache = LruMeshCache(budget_bytes=100)
    cache.put("a", "A", 40)
    cache.put("a", "A2", 60)
    assert cache.stats() == {"entries": 1, "size_bytes": 60, "hits": 0, "misses": 0}


def test_values_over_budget_are_not_stored() -> None:
    cache = LruMeshCache(budget_bytes=10)
    cache.put("big", "B", 11)
    assert cache.get("big") is None
    assert cache.stats()["entries"] == 0
