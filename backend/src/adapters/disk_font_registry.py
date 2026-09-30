"""Built-in fonts from ``fonts/`` plus an LRU of parsed custom fonts.

``fonts/index.json`` lists the built-ins: ``key``, ``name``, ``single_story_a``,
``ttf`` and ``woff2`` file names. Custom fonts are never stored; they are parsed
from the bytes embedded in the config and cached by sha256 (decision D18).
"""

import json
import threading
from collections import OrderedDict
from pathlib import Path

from fontTools.ttLib import TTFont

from src.core.config.models import FontRef
from src.core.engine.text import Glyphs
from src.core.exceptions import InvalidConfig, InvalidFont
from src.core.interfaces.dtos import FontInfo
from src.core.interfaces.font_parser import FontParser
from src.core.interfaces.font_registry import FontRegistry

_CUSTOM_CACHE_SIZE = 16


class DiskFontRegistry(FontRegistry):
    def __init__(self, fonts_dir: Path, parser: FontParser) -> None:
        self._dir = fonts_dir
        self._parser = parser
        self._lock = threading.Lock()
        self._builtin: dict[str, Glyphs] = {}
        self._custom: OrderedDict[str, Glyphs] = OrderedDict()
        self._index = self._read_index()

    def _read_index(self) -> dict[str, FontInfo]:
        index_path = self._dir / "index.json"
        if not index_path.is_file():
            return {}
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        return {entry["key"]: FontInfo(**entry) for entry in entries}

    def list(self) -> list[FontInfo]:
        return list(self._index.values())

    def glyphs(self, font: FontRef) -> Glyphs:
        if font.custom is not None:
            return self._custom_glyphs(font)
        info = self._index.get(font.key)
        if info is None:
            known = ", ".join(sorted(self._index)) or "none"
            raise InvalidConfig(
                f"unknown font key '{font.key}' (available: {known})",
                [{"loc": ["font", "key"], "msg": "unknown font key", "code": "font_unknown"}],
            )
        with self._lock:
            glyphs = self._builtin.get(info.key)
            if glyphs is None:
                try:
                    ttf = TTFont(self._dir / info.ttf, lazy=False)
                except Exception as exc:
                    raise InvalidFont(f"built-in font '{info.key}' failed to load: {exc}") from exc
                glyphs = self._builtin[info.key] = Glyphs(ttf, font_id=font.cache_id)
            return glyphs

    def _custom_glyphs(self, font: FontRef) -> Glyphs:
        sha256 = font.custom.sha256
        with self._lock:
            cached = self._custom.get(sha256)
            if cached is not None:
                self._custom.move_to_end(sha256)
                return cached
        parsed = self._parser.parse(font.custom.decoded())
        with self._lock:
            self._custom[sha256] = parsed.glyphs
            if len(self._custom) > _CUSTOM_CACHE_SIZE:
                self._custom.popitem(last=False)
        return parsed.glyphs
