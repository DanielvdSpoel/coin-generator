"""Command line front end to the engine.

    uv run python -m src.cli build design.coin.json out.stl
    uv run python -m src.cli build design.coin.json out.glb --quality preview
    uv run python -m src.cli validate design.coin.json
    uv run python -m src.cli svg design.coin.json --face front > front.svg
    uv run python -m src.cli bench design.coin.json
    uv run python -m src.cli filaments-snapshot
    uv run python -m src.cli openapi > openapi.json

The output format of ``build`` follows the file extension: ``.stl`` (single
material), ``.glb`` (preview with materials), ``.3mf`` (two-tone print file) or
``.zip`` (body.stl + enamel.stl).
"""

import argparse
import json
import sys
import time
from pathlib import Path

from src.adapters.filamentcolors_source import (
    FilamentColorsSource,
    SnapshotFilamentSource,
    write_snapshot,
)
from src.container import Container, get_container
from src.core.config.defaults import default_config
from src.core.config.migrate import load_config
from src.core.config.models import CoinConfig
from src.core.engine import export
from src.core.engine.build import build_coin
from src.core.engine.materials import classify_faces, enamel_volumes
from src.core.engine.quality import EXPORT, PREVIEW, quality_for
from src.core.engine.svg import face_svg
from src.core.exceptions import CoinError
from src.core.services.colors import resolve_colors

FORMATS = (".stl", ".glb", ".3mf", ".zip")


def _read_config(path: str) -> CoinConfig:
    if path == "default":
        return default_config()
    return load_config(json.loads(Path(path).read_text(encoding="utf-8")))


def build_bytes(config: CoinConfig, suffix: str, quality_name: str, container: Container) -> bytes:
    glyphs = container.font_registry().glyphs(config.font)
    colors = resolve_colors(config, container.filament_registry())
    built = build_coin(config, glyphs, quality_for(quality_name))
    if suffix == ".stl":
        return export.to_stl(built.mesh)
    if suffix == ".glb":
        return export.to_glb(built.mesh, classify_faces(built), colors)
    volumes = enamel_volumes(built)
    if suffix == ".3mf":
        return export.to_3mf(volumes, colors, title=config.meta.name or "coin")
    return export.to_stl_pair(volumes)


def _cmd_build(args: argparse.Namespace, container: Container) -> int:
    out = Path(args.out)
    suffix = out.suffix.lower()
    if suffix not in FORMATS:
        print(f"error: output must end in one of {', '.join(FORMATS)}", file=sys.stderr)
        return 2
    config = _read_config(args.config)
    started = time.perf_counter()
    data = build_bytes(config, suffix, args.quality, container)
    out.write_bytes(data)
    elapsed = time.perf_counter() - started
    print(f"wrote {out} ({len(data) / 1024:.0f} kB, {args.quality} quality, {elapsed:.2f} s)")
    return 0


def _cmd_validate(args: argparse.Namespace, container: Container) -> int:
    config = _read_config(args.config)
    warnings = container.validation_service().validate(config)
    for warning in warnings:
        print(f"{warning.severity:5}  {warning.code}  {warning.path}: {warning.msg}")
    errors = sum(1 for warning in warnings if warning.severity == "error")
    print(f"valid config, {len(warnings)} warning(s), {errors} of them errors")
    return 1 if errors else 0


def _cmd_svg(args: argparse.Namespace, container: Container) -> int:
    config = _read_config(args.config)
    glyphs = container.font_registry().glyphs(config.font)
    colors = resolve_colors(config, container.filament_registry())
    sys.stdout.write(face_svg(config, args.face, glyphs, colors, quality_for(args.quality)))
    return 0


def _cmd_bench(args: argparse.Namespace, container: Container) -> int:
    config = _read_config(args.config)
    glyphs = container.font_registry().glyphs(config.font)
    build_coin(config, glyphs, PREVIEW)  # warm the glyph cache and the imports
    print(f"{'quality':8} {'2d':>8} {'extrude':>8} {'union':>8} {'total':>8} {'faces':>8}")
    for quality in (PREVIEW, EXPORT):
        best = None
        for _ in range(args.runs):
            started = time.perf_counter()
            built = build_coin(config, glyphs, quality)
            total = time.perf_counter() - started
            if best is None or total < best[0]:
                best = (total, built)
        total, built = best
        stages = " ".join(f"{built.timings[s] * 1e3:6.0f}ms" for s in ("2d", "extrude", "union"))
        print(f"{quality.name:8} {stages} {total * 1e3:6.0f}ms {len(built.mesh.faces):8}")
    return 0


def _cmd_openapi(args: argparse.Namespace, container: Container) -> int:
    from src.main import create_app

    schema = create_app(container, warm=False).openapi()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _cmd_filaments_snapshot(args: argparse.Namespace, container: Container) -> int:
    settings = container.settings
    path = settings.data_dir / "filaments.snapshot.json"
    source = FilamentColorsSource(
        settings.filamentcolors_url,
        fallback=SnapshotFilamentSource(path),
        timeout=settings.filamentcolors_timeout_s,
    )
    count = write_snapshot(source, settings.filamentcolors_url, path)
    print(f"wrote {path} ({count} swatches)")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coin", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    config_help = "path to a .coin.json file, or 'default' for the built-in starting design"

    build = sub.add_parser("build", help="build a coin file")
    build.add_argument("config", help=config_help)
    build.add_argument("out", help="output path: .stl, .glb, .3mf or .zip")
    build.add_argument("--quality", choices=("preview", "export"), default="export")
    build.set_defaults(run=_cmd_build)

    validate = sub.add_parser("validate", help="check a config and list printability warnings")
    validate.add_argument("config", help=config_help)
    validate.set_defaults(run=_cmd_validate)

    svg = sub.add_parser("svg", help="write one face as SVG to stdout")
    svg.add_argument("config", help=config_help)
    svg.add_argument("--face", choices=("front", "back"), default="front")
    svg.add_argument("--quality", choices=("preview", "export"), default="export")
    svg.set_defaults(run=_cmd_svg)

    bench = sub.add_parser("bench", help="print build stage timings for both qualities")
    bench.add_argument("config", help=config_help)
    bench.add_argument("--runs", type=int, default=3, help="runs per quality; the best is shown")
    bench.set_defaults(run=_cmd_bench)

    openapi = sub.add_parser("openapi", help="print the OpenAPI schema as JSON")
    openapi.set_defaults(run=_cmd_openapi)

    snapshot = sub.add_parser(
        "filaments-snapshot", help="refresh data/filaments.snapshot.json from filamentcolors.xyz"
    )
    snapshot.set_defaults(run=_cmd_filaments_snapshot)
    return parser


def main(argv: list[str] | None = None, container: Container | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args, container or get_container())
    except (CoinError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
