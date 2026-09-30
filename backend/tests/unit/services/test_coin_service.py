import time
from unittest.mock import Mock

import pytest

from src.adapters.lru_mesh_cache import LruMeshCache
from src.core.config.defaults import default_config
from src.core.engine.build import BuiltCoin
from src.core.engine.quality import EXPORT, PREVIEW
from src.core.exceptions import BuildTimeout, NotWatertight
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.interfaces.mesh_cache import MeshCache
from src.core.services.coin_service import BuildExecutor, CoinService, slugify
from src.core.services.validation_service import ValidationService
from tests.conftest import config_with


@pytest.fixture
def fonts(glyphs) -> Mock:
    registry = Mock(FontRegistry)
    registry.glyphs.return_value = glyphs
    return registry


@pytest.fixture
def filaments() -> Mock:
    registry = Mock(FilamentRegistry)
    registry.resolve.side_effect = lambda ref: ref.hex or "#dca256"
    return registry


@pytest.fixture
def cache() -> Mock:
    cache = Mock(MeshCache)
    cache.get.return_value = None
    return cache


def _service(fonts, filaments, cache, executor=None) -> CoinService:
    validation = ValidationService(fonts, filaments)
    return CoinService(fonts, filaments, cache, executor or BuildExecutor(1, 30), validation)


def test_cache_hit_skips_the_build(fonts, filaments, cache, built_default: BuiltCoin) -> None:
    cache.get.return_value = built_default
    service = _service(fonts, filaments, cache)
    assert service.build(default_config(), PREVIEW) is built_default
    fonts.glyphs.assert_not_called()
    cache.put.assert_not_called()


def test_build_stores_the_mesh_under_the_geometry_hash(fonts, filaments, cache) -> None:
    service = _service(fonts, filaments, cache)
    built = service.build(default_config(), PREVIEW)
    assert built.mesh.is_watertight
    key, value, size = cache.put.call_args.args
    assert key.startswith("mesh:preview:") and value is built and size > 0


def test_glb_reuses_the_mesh_across_colour_changes(fonts, filaments, built_default) -> None:
    store: dict = {}
    cache = Mock(MeshCache)
    cache.get.side_effect = store.get
    cache.put.side_effect = lambda key, value, size: store.__setitem__(key, value)
    service = _service(fonts, filaments, cache)

    first = service.build_glb(default_config(), "preview")
    recoloured = config_with(**{"faces.front.inlay": {"hex": "#ff0000"}})
    second = service.build_glb(recoloured, "preview")

    assert first.etag != second.etag
    assert not first.cached and not second.cached
    assert len([k for k in store if k.startswith("mesh:")]) == 1  # one geometry, built once
    assert len([k for k in store if k.startswith("glb:")]) == 2
    third = service.build_glb(recoloured, "preview")
    assert third.cached and third.data == second.data


def test_timeout_maps_to_build_timeout(fonts, filaments, cache, monkeypatch) -> None:
    def slow(*args, **kwargs):
        time.sleep(0.5)

    monkeypatch.setattr("src.core.services.coin_service.build_coin", slow)
    service = _service(fonts, filaments, cache, BuildExecutor(1, 0.05))
    with pytest.raises(BuildTimeout, match="0.05 s"):
        service.build(default_config(), PREVIEW)


def test_export_refuses_a_leaky_mesh(fonts, filaments, cache, built_default, monkeypatch) -> None:
    leaky = built_default.mesh.copy()
    leaky.update_faces([i != 0 for i in range(len(leaky.faces))])
    cache.get.return_value = BuiltCoin(**{**vars(built_default), "mesh": leaky, "quality": EXPORT})
    service = _service(fonts, filaments, cache)
    with pytest.raises(NotWatertight):
        service.export(default_config(), "stl")


def test_export_names_the_file_after_the_design(fonts, filaments, cache) -> None:
    service = _service(fonts, filaments, cache)
    config = config_with(**{"meta.name": "Crypto Analyse Team!", "size.diameter_mm": 40})
    result = service.export(config, "stl")
    assert result.filename == "crypto-analyse-team.stl"
    assert result.media_type == "model/stl"
    assert {w.code for w in result.warnings} == {"thin_stroke"}
    assert result.data[:80] == bytes(80)


def test_validate_returns_the_normalised_config(fonts, filaments, cache) -> None:
    from src.core.exceptions import UnknownFilament

    def resolve(ref):
        if ref.filament == "gone":
            raise UnknownFilament("gone")
        return ref.hex or "#dca256"

    filaments.resolve.side_effect = resolve
    service = _service(fonts, filaments, cache)
    result = service.validate(config_with(**{"colors.relief": {"filament": "gone"}}))
    assert result.ok
    assert result.config.colors.relief.hex == "#808080"
    assert [w.code for w in result.warnings] == ["filament_unknown"]


def test_slugify() -> None:
    assert slugify("  CAT Oost-Nederland ") == "cat-oost-nederland"
    assert slugify("") == "coin"
    assert slugify("!!!", "design") == "design"
    assert len(slugify("x" * 100)) == 60


def test_cached_meshes_carry_no_derived_arrays(fonts, filaments) -> None:
    """Derived trimesh arrays cost ~14x the mesh itself; the cache must not keep them."""
    cache = LruMeshCache(64 * 1024 * 1024)
    service = _service(fonts, filaments, cache)
    config = default_config()
    service.build_glb(config)
    service.stats(config)
    built = cache.get(next(k for k in cache._entries if k.startswith("mesh:")))
    assert len(built.mesh._cache.cache) == 0
