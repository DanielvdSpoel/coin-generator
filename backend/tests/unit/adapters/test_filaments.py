import json

import pytest

from src.adapters.filamentcolors_source import (
    FilamentColorsSource,
    SnapshotFilamentSource,
    swatch_from_api,
    write_snapshot,
)
from src.adapters.memory_filament_registry import MemoryFilamentRegistry, load_overrides
from src.core.config.models import ColorRef
from src.core.exceptions import UnknownFilament
from src.core.interfaces.dtos import FilamentVersion, Swatch
from src.core.interfaces.filament_source import FilamentSource
from src.settings import BACKEND_DIR

BASE = "https://filaments.test"


def _api_item(swatch_id: int, hex_color: str = "E9EDED", **extra) -> dict:
    return {
        "id": swatch_id,
        "slug": f"acme-white-pla-{swatch_id}",
        "manufacturer": {"id": 1, "name": "Acme"},
        "color_name": "White",
        "filament_type": {"id": 2, "name": "PLA Matte", "parent_type": {"name": "PLA"}},
        "hex_color": hex_color,
        "published": True,
        **extra,
    }


def _swatch(swatch_id: str, hex_value: str, name: str = "Colour") -> Swatch:
    return Swatch(swatch_id, name, "Acme", "PLA", "PLA Matte", hex_value)


class FakeSource(FilamentSource):
    def __init__(self, swatches: list[Swatch], version: int = 1) -> None:
        self.swatches = swatches
        self._version = version

    def fetch_all(self) -> list[Swatch]:
        return self.swatches

    def version(self) -> FilamentVersion:
        return FilamentVersion(self._version, 1000, "then")


def test_swatch_mapping_from_the_upstream_shape() -> None:
    swatch = swatch_from_api(_api_item(4835), BASE)
    assert swatch == Swatch(
        id="fc-4835",
        name="White",
        vendor="Acme",
        material="PLA",
        finish="PLA Matte",
        hex="#e9eded",
        source_url=f"{BASE}/swatch/acme-white-pla-4835/",
    )


@pytest.mark.parametrize(
    "item",
    [_api_item(1, hex_color=""), _api_item(2, hex_color="nothex"), _api_item(3, published=False)],
)
def test_unusable_swatches_are_skipped(item: dict) -> None:
    assert swatch_from_api(item, BASE) is None


def test_live_source_follows_pagination() -> None:
    pages = {
        f"{BASE}/api/swatch/?page_size=2": {
            "results": [_api_item(1), _api_item(2)],
            "next": f"{BASE}/api/swatch/?page=2&page_size=2",
        },
        f"{BASE}/api/swatch/?page=2&page_size=2": {"results": [_api_item(3)], "next": None},
        f"{BASE}/api/version/": {"db_version": 7, "db_last_modified": 123},
    }
    source = FilamentColorsSource(
        BASE + "/", fallback=FakeSource([]), page_size=2, fetch_json=pages.__getitem__
    )
    assert [s.id for s in source.fetch_all()] == ["fc-1", "fc-2", "fc-3"]
    version = source.version()
    assert (version.db_version, version.db_last_modified) == (7, 123)
    assert version.refreshed_at is not None


def test_live_source_falls_back_to_the_snapshot_when_the_network_fails() -> None:
    def boom(url: str):
        raise OSError("network unreachable")

    fallback = FakeSource([_swatch("fc-9", "#010203")], version=3)
    source = FilamentColorsSource(BASE, fallback=fallback, fetch_json=boom)
    assert source.fetch_all() == fallback.swatches
    assert source.version().db_version == 3


def test_live_source_falls_back_when_upstream_is_empty_or_malformed() -> None:
    fallback = FakeSource([_swatch("fc-9", "#010203")])
    empty = FilamentColorsSource(BASE, fallback, fetch_json=lambda url: {"results": []})
    assert empty.fetch_all() == fallback.swatches
    malformed = FilamentColorsSource(BASE, fallback, fetch_json=lambda url: {"oops": 1})
    assert malformed.fetch_all() == fallback.swatches


def test_snapshot_round_trip(tmp_path) -> None:
    pages = {
        f"{BASE}/api/swatch/?page_size=100": {
            "results": [_api_item(2), _api_item(1)],
            "next": None,
        },
        f"{BASE}/api/version/": {"db_version": 7, "db_last_modified": 123},
    }
    path = tmp_path / "snapshot.json"
    live = FilamentColorsSource(BASE, fallback=FakeSource([]), fetch_json=pages.__getitem__)
    assert write_snapshot(live, BASE, path) == 2

    assert json.loads(path.read_text(encoding="utf-8"))["source"] == BASE
    snapshot = SnapshotFilamentSource(path)
    assert [s.id for s in snapshot.fetch_all()] == ["fc-1", "fc-2"]
    assert snapshot.version().db_version == 7
    assert SnapshotFilamentSource(tmp_path / "missing.json").fetch_all() == []


def test_registry_resolves_overrides_before_upstream() -> None:
    snapshot = FakeSource([_swatch("fc-1", "#111111"), _swatch("fc-2", "#222222")])
    overrides = [_swatch("fc-1", "#AAAAAA"), _swatch("local-gold", "#DCA256")]
    registry = MemoryFilamentRegistry(snapshot, overrides)

    assert registry.resolve(ColorRef(filament="fc-1")) == "#aaaaaa"
    assert registry.resolve(ColorRef(filament="fc-2")) == "#222222"
    assert registry.resolve(ColorRef(filament="local-gold")) == "#dca256"
    sources = {f.id: f.hex_source for f in registry.list()}
    assert sources == {"fc-1": "override", "fc-2": "measured", "local-gold": "override"}


def test_hex_references_pass_through() -> None:
    registry = MemoryFilamentRegistry(FakeSource([]), [])
    assert registry.resolve(ColorRef(hex="#C9A468")) == "#c9a468"


def test_unknown_filament_id_raises() -> None:
    registry = MemoryFilamentRegistry(FakeSource([_swatch("fc-1", "#111111")]), [])
    with pytest.raises(UnknownFilament, match="fc-404"):
        registry.resolve(ColorRef(filament="fc-404"))
    with pytest.raises(UnknownFilament):
        registry.finish(ColorRef(filament="fc-404"))


def test_refresh_swaps_in_live_data_and_keeps_overrides() -> None:
    snapshot = FakeSource([_swatch("fc-1", "#111111")], version=1)
    live = FakeSource([_swatch("fc-1", "#333333"), _swatch("fc-5", "#555555")], version=2)
    registry = MemoryFilamentRegistry(snapshot, [_swatch("local-gold", "#dca256")], live=live)
    assert registry.version().db_version == 1

    registry.refresh()
    assert registry.version().db_version == 2
    assert registry.resolve(ColorRef(filament="fc-1")) == "#333333"
    assert registry.resolve(ColorRef(filament="fc-5")) == "#555555"
    assert registry.resolve(ColorRef(filament="local-gold")) == "#dca256"


def test_registry_serves_the_snapshot_when_the_live_source_raises() -> None:
    def boom(url: str):
        raise TimeoutError("upstream timed out")

    snapshot = FakeSource([_swatch("fc-1", "#111111")])
    live = FilamentColorsSource(BASE, fallback=snapshot, fetch_json=boom)
    registry = MemoryFilamentRegistry(snapshot, [], live=live)
    registry.refresh()
    assert registry.resolve(ColorRef(filament="fc-1")) == "#111111"


def test_background_refresh_is_off_without_a_live_source_or_interval() -> None:
    registry = MemoryFilamentRegistry(FakeSource([]), [], live=None, refresh_hours=6)
    registry.start_background_refresh()
    assert registry._thread is None
    registry = MemoryFilamentRegistry(FakeSource([]), [], live=FakeSource([]), refresh_hours=0)
    registry.start_background_refresh()
    assert registry._thread is None


def test_background_refresh_runs_and_stops() -> None:
    live = FakeSource([_swatch("fc-5", "#555555")], version=2)
    registry = MemoryFilamentRegistry(FakeSource([]), [], live=live, refresh_hours=1)
    registry.start_background_refresh()
    registry.stop_background_refresh()
    registry._thread.join(timeout=5)
    assert not registry._thread.is_alive()
    assert registry.resolve(ColorRef(filament="fc-5")) == "#555555"


def test_committed_data_files_load(engine_container) -> None:
    overrides = load_overrides(BACKEND_DIR / "data" / "filaments.overrides.json")
    assert {o.id for o in overrides} >= {
        "local-bambu-pla-silk-gold",
        "local-bambu-pla-matte-dark-blue",
    }
    registry = engine_container.filament_registry()
    assert len(registry.list()) > 2000
    assert registry.version().db_version is not None
    # The colorimeter values from coin-tool-addendum.md §2.
    assert registry.resolve(ColorRef(filament="local-bambu-pla-silk-gold")) == "#dca256"
    assert registry.resolve(ColorRef(filament="local-bambu-pla-silk-silver")) == "#b9c0c4"
    assert registry.resolve(ColorRef(filament="local-bambu-pla-matte-dark-blue")) == "#395064"
    assert registry.resolve(ColorRef(filament="local-bambu-pla-basic-blue")) == "#0a2989"
    assert registry.finish(ColorRef(filament="local-bambu-pla-silk-gold")) == "PLA Silk+"
    assert registry.finish(ColorRef(hex="#c9a468")) == ""
    assert load_overrides(BACKEND_DIR / "data" / "nope.json") == []


def test_version_etag_follows_the_data_and_the_overrides() -> None:
    source = FakeSource([_swatch("fc-1", "#111111")])
    plain = MemoryFilamentRegistry(source, [])
    same = MemoryFilamentRegistry(FakeSource([_swatch("fc-1", "#111111")], version=2), [])
    changed = MemoryFilamentRegistry(FakeSource([_swatch("fc-1", "#222222")]), [])
    overridden = MemoryFilamentRegistry(source, [_swatch("fc-1", "#333333")])

    assert plain.version().etag == same.version().etag
    assert len({plain.version().etag, changed.version().etag, overridden.version().etag}) == 3
