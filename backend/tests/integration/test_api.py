"""Every endpoint's happy path and the error shapes, against the real app factory."""

import io
import json
import time
import zipfile

import pytest
import trimesh
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from src.core.config.defaults import default_config
from src.settings import BACKEND_DIR
from tests.conftest import config_with, golden_config


def _body(config=None) -> dict:
    return {"config": (config or default_config()).to_json_dict()}


def _png() -> bytes:
    image = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse([10, 10, 110, 110], fill=(0, 0, 0, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# --- coin ---------------------------------------------------------------------------


def test_validate_happy_path(api: TestClient) -> None:
    response = api.post("/api/validate", json=_body())
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True and body["warnings"] == []
    assert body["config"]["schema_version"] == 1
    assert body["config"]["faces"]["front"]["icon"] is None


def test_validate_lists_warnings(api: TestClient) -> None:
    response = api.post("/api/validate", json=_body(config_with(**{"size.diameter_mm": 40})))
    codes = {w["code"] for w in response.json()["warnings"]}
    assert "thin_stroke" in codes


def test_422_names_the_offending_field(api: TestClient) -> None:
    bad = _body()
    bad["config"]["rings"]["r_inlay"] = 150
    response = api.post("/api/validate", json=bad)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"][:2] == ["body", "config"]
    assert "r_inlay" in detail[0]["msg"]
    assert set(detail[0]) == {"loc", "msg", "code"}


def test_422_for_an_unknown_filament_names_the_path(api: TestClient) -> None:
    config = config_with(**{"faces.back.inlay": {"filament": "fc-does-not-exist"}})
    response = api.post("/api/preview/glb", json=_body(config))
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["faces", "back", "inlay"]
    assert response.json()["detail"][0]["code"] == "filament_unknown"


def test_preview_svg(api: TestClient) -> None:
    response = api.post("/api/preview/svg", json={**_body(), "face": "back"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert 'data-face="back"' in response.text


def test_preview_glb_with_etag_round_trip(api: TestClient) -> None:
    body = _body(golden_config("fancy-example"))
    first = api.post("/api/preview/glb", json=body)
    assert first.status_code == 200
    assert first.headers["content-type"] == "model/gltf-binary"
    etag = first.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')

    scene = trimesh.load(io.BytesIO(first.content), file_type="glb")
    assert set(scene.geometry) == {"relief", "inlay_front", "inlay_back"}

    again = api.post("/api/preview/glb", json=body, headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""

    warm = api.post("/api/preview/glb", json=body)
    assert warm.status_code == 200 and warm.headers["x-cache"] == "hit"


def test_preview_glb_is_fast_when_warm(api: TestClient) -> None:
    body = _body()
    api.post("/api/preview/glb", json=body)
    started = time.perf_counter()
    for _ in range(5):
        assert api.post("/api/preview/glb", json=body).status_code == 200
    assert (time.perf_counter() - started) / 5 < 0.1


@pytest.mark.parametrize(
    ("fmt", "media_type", "extension"),
    [
        ("stl", "model/stl", "stl"),
        ("3mf", "model/3mf", "3mf"),
        ("stl-pair", "application/zip", "zip"),
    ],
)
def test_export_formats(api: TestClient, fmt: str, media_type: str, extension: str) -> None:
    config = config_with(**{"meta.name": "My Coin", "size.diameter_mm": 40})
    response = api.post("/api/export", json={**_body(config), "format": fmt})
    assert response.status_code == 200
    assert response.headers["content-type"] == media_type
    assert response.headers["content-disposition"] == f'attachment; filename="my-coin.{extension}"'
    assert response.headers["x-coin-warnings"] == "thin_stroke"
    if fmt == "stl":
        assert trimesh.load(io.BytesIO(response.content), file_type="stl").is_watertight
    elif fmt == "3mf":
        scene = trimesh.load(io.BytesIO(response.content), file_type="3mf")
        assert set(scene.geometry) == {"body", "enamel_front", "enamel_back"}
    else:
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert archive.namelist() == ["body.stl", "enamel.stl"]


def test_export_refuses_a_leaky_mesh(api: TestClient, engine_container, monkeypatch) -> None:
    from src.core.services import coin_service

    real_build = coin_service.build_coin

    def leaky(config, glyphs, quality):
        built = real_build(config, glyphs, quality)
        built.mesh.update_faces([i != 0 for i in range(len(built.mesh.faces))])
        return built

    monkeypatch.setattr(coin_service, "build_coin", leaky)
    config = config_with(**{"meta.name": "leaky test coin"})  # a fresh geometry, not cached
    response = api.post("/api/export", json={**_body(config), "format": "stl"})
    assert response.status_code == 500
    assert response.json()["detail"][0]["code"] == "not_watertight"


def test_build_timeout_is_a_503(api: TestClient, engine_container, monkeypatch) -> None:
    from src.core.services import coin_service

    real_build = coin_service.build_coin

    def slow(config, glyphs, quality):
        time.sleep(0.3)
        return real_build(config, glyphs, quality)

    monkeypatch.setattr(coin_service, "build_coin", slow)
    monkeypatch.setattr(engine_container.build_executor(), "_timeout", 0.05)
    config = config_with(**{"faces.front.top_text.text": "SLOW BUILD"})
    response = api.post("/api/preview/glb", json=_body(config))
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert response.json()["detail"][0]["code"] == "build_timeout"


def test_json_bodies_over_the_limit_are_rejected(api: TestClient, engine_container) -> None:
    limit = engine_container.settings.max_json_bytes
    response = api.post(
        "/api/validate",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(limit + 1)},
    )
    assert response.status_code == 413
    assert response.json()["detail"][0]["code"] == "payload_too_large"


def test_config_schema(api: TestClient) -> None:
    schema = api.get("/api/schema/coin-config").json()
    assert schema["title"] == "CoinConfig"
    assert "IconGeometry" in schema["$defs"]


# --- catalog ------------------------------------------------------------------------


def test_fonts_and_font_files(api: TestClient) -> None:
    fonts = api.get("/api/fonts").json()
    assert {f["key"] for f in fonts} == {"poppins-semibold", "poppins-medium"}
    assert fonts[0]["woff2_url"] == f"/api/fonts/{fonts[0]['key']}.woff2"
    response = api.get(fonts[0]["woff2_url"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "font/woff2"
    assert response.content[:4] == b"wOF2"
    assert "immutable" in response.headers["cache-control"]
    assert api.get("/api/fonts/nope.woff2").status_code == 404


def test_font_inspect(api: TestClient) -> None:
    data = (BACKEND_DIR / "fonts" / "Poppins-Medium.woff2").read_bytes()
    response = api.post("/api/fonts/inspect", files={"file": ("Poppins.woff2", data)})
    assert response.status_code == 200
    body = response.json()
    assert body["family"] == "Poppins" and body["format"] == "woff2"
    assert body["sample_svg"].startswith("<svg") and body["warnings"] == []
    assert len(body["sha256"]) == 64

    bad = api.post("/api/fonts/inspect", files={"file": ("x.ttf", b"garbage")})
    assert bad.status_code == 422
    assert bad.json()["detail"][0]["code"] == "invalid_font"


def test_filaments_filter_and_version(api: TestClient) -> None:
    all_items = api.get("/api/filaments").json()
    assert len(all_items) > 2000
    bambu = api.get("/api/filaments", params={"vendor": "bambu lab"}).json()
    assert bambu and all(f["vendor"] == "Bambu Lab" for f in bambu)
    gold = api.get("/api/filaments", params={"q": "silk gold", "vendor": "Bambu Lab"}).json()
    assert any(f["id"] == "local-bambu-pla-silk-gold" for f in gold)
    assert {f["hex_source"] for f in gold} <= {"measured", "override"}
    version = api.get("/api/filaments/version").json()
    assert version["db_version"] is not None


def test_presets_and_templates(api: TestClient) -> None:
    presets = api.get("/api/presets").json()
    assert {p["id"] for p in presets} == {"fancy", "simple"}
    assert presets[0]["patch"]["edge"]

    templates = api.get("/api/templates").json()
    assert {t["id"] for t in templates} == {"fancy-example", "simple-example"}
    for template in templates:
        assert template["thumbnail_svg"].startswith("<svg")
        assert api.post("/api/validate", json={"config": template["config"]}).status_code == 200


# --- icons --------------------------------------------------------------------------


def test_icon_trace_png(api: TestClient) -> None:
    options = json.dumps({"simplify": 0.5, "embed_source": True})
    response = api.post(
        "/api/icons/trace",
        files={"file": ("dot.png", _png(), "image/png")},
        data={"options": options},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["parts"] == 1 and body["holes"] == 0
    assert body["preview_svg"].startswith("<svg")
    assert body["geometry"]["source"]["filename"] == "dot.png"
    assert body["geometry"]["source"]["data_url"].startswith("data:image/png;base64,")
    assert body["geometry"]["source"]["trace"]["simplify"] == 0.5
    assert max(abs(v) for v in body["bbox"]) == pytest.approx(100, abs=2)

    config = default_config().to_json_dict()
    config["faces"]["front"]["icon"] = {"geometry": body["geometry"], "fit": 0.8}
    assert api.post("/api/validate", json={"config": config}).status_code == 200


def test_icon_trace_rejects_svg_and_garbage(api: TestClient) -> None:
    svg = api.post("/api/icons/trace", files={"file": ("logo.svg", b"<svg/>", "image/svg+xml")})
    assert svg.status_code == 422 and "SVG" in svg.json()["detail"][0]["msg"]
    garbage = api.post("/api/icons/trace", files={"file": ("x.png", b"nope", "image/png")})
    assert garbage.status_code == 422
    assert garbage.json()["detail"][0]["code"] == "trace_failed"
    bad_options = api.post(
        "/api/icons/trace", files={"file": ("d.png", _png())}, data={"options": "{bad"}
    )
    assert bad_options.status_code == 422
    assert bad_options.json()["detail"][0]["loc"] == ["options"]


# --- contact ------------------------------------------------------------------------


def _contact(**overrides) -> dict:
    return {
        "name": "Sam",
        "email": "sam@example.com",
        "message": "One coin please",
        "attach_design": False,
        "honeypot": "",
        "started_at": time.time() - 10,
        **overrides,
    }


def test_contact_without_attachment(api: TestClient, engine_container) -> None:
    mailer = engine_container.mailer()
    mailer.sent.clear()
    response = api.post("/api/contact", json=_contact())
    assert response.status_code == 202 and response.json() == {}
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["to"] == engine_container.settings.contact_to
    assert "sam@example.com" in mailer.sent[0]["text"]
    assert mailer.sent[0]["attachments"] == []


def test_contact_with_attachment(api: TestClient, engine_container) -> None:
    mailer = engine_container.mailer()
    mailer.sent.clear()
    config = config_with(**{"meta.name": "Team Coin"}).to_json_dict()
    response = api.post("/api/contact", json=_contact(attach_design=True, config=config))
    assert response.status_code == 202
    attachments = mailer.sent[0]["attachments"]
    assert [a.filename for a in attachments] == ["team-coin.coin.json", "team-coin-front.svg"]
    assert json.loads(attachments[0].content)["meta"]["name"] == "Team Coin"
    assert attachments[1].content.startswith(b"<svg")


def test_contact_rejects_bots(api: TestClient) -> None:
    honeypot = api.post("/api/contact", json=_contact(honeypot="http://spam"))
    assert honeypot.status_code == 422
    assert honeypot.json()["detail"][0]["loc"] == ["honeypot"]
    fast = api.post("/api/contact", json=_contact(started_at=time.time()))
    assert fast.status_code == 422
    assert fast.json()["detail"][0]["code"] == "spam"
    missing = api.post("/api/contact", json=_contact(attach_design=True))
    assert missing.status_code == 422 and missing.json()["detail"][0]["loc"] == ["config"]
    bad_email = api.post("/api/contact", json=_contact(email="not-an-email"))
    assert bad_email.status_code == 422


def test_docs_are_hidden_outside_dev(api: TestClient) -> None:
    assert api.get("/api/docs").status_code == 404
    assert api.get("/api/openapi.json").status_code == 200
