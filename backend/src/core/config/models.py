"""``CoinConfig`` v1: the one object every part of the tool is a function of.

Radii and offsets are in design units (320 = coin diameter, decision D13);
thicknesses are in millimetres. The contract is documented in
``docs/plan/02-data-model-and-api.md``; this module enforces it.

Checks that need a registry (does the font key exist, does the filament id resolve,
does the custom font parse) happen where the registry is available, not here.
"""

import base64
import binascii
import hashlib
import math
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = 1

DESIGN_DIAMETER = 320.0
R_EDGE = DESIGN_DIAMETER / 2
MIN_RING_GAP = 2.0
TEXT_BAND_MARGIN = 4.0
MAX_TEXT_LENGTH = 40
ICON_RADIUS = 100.0
ICON_RADIUS_TOLERANCE = 0.01
"""Slack for coordinates that were rounded when the icon was serialised."""
MAX_ICON_VERTICES = 50_000
MAX_FONT_BYTES = 2 * 1024 * 1024

FaceName = Literal["front", "back"]
Point2D = tuple[float, float]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Meta(BaseModel):
    """Free-form, excluded from hashing."""

    model_config = ConfigDict(extra="allow")

    name: str = ""
    notes: str = ""
    created_with: str = ""


class Size(_Model):
    diameter_mm: float = Field(50.0, ge=30, le=100)
    body_mm: float = Field(2.5, ge=1.0, le=6.0)
    relief_mm: float = Field(0.7, ge=0.3, le=2.0)


class Edge(_Model):
    style: Literal["plain", "reeded"] = "reeded"
    teeth: int = Field(120, ge=40, le=300)
    depth: float = Field(2.0, ge=0.5, le=5.0)


class Rings(_Model):
    r_edge: float = R_EDGE
    r_rim: float = 151.0
    r_inlay: float = 143.0
    divider: bool = True
    r_div_out: float = 113.0
    r_div_in: float = 101.0

    @model_validator(mode="after")
    def _ordering(self) -> Self:
        if self.r_edge != R_EDGE:
            raise ValueError(f"r_edge is fixed at {R_EDGE:g} in schema version 1")
        if self.r_div_in < 10:
            raise ValueError("r_div_in must be at least 10")
        chain = [
            ("r_div_in", self.r_div_in),
            ("r_div_out", self.r_div_out),
            ("r_inlay", self.r_inlay),
            ("r_rim", self.r_rim),
            ("r_edge", self.r_edge),
        ]
        for (inner_name, inner), (outer_name, outer) in zip(chain, chain[1:], strict=False):
            if inner + MIN_RING_GAP > outer:
                raise ValueError(
                    f"{inner_name} ({inner:g}) must be at least {MIN_RING_GAP:g} units "
                    f"below {outer_name} ({outer:g})"
                )
        return self


class CustomFont(_Model):
    """A user-uploaded font, embedded so the template stays self-contained (D18)."""

    name: str = Field(max_length=120)
    format: Literal["ttf", "otf", "woff", "woff2"]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    data: str

    def decoded(self) -> bytes:
        return base64.b64decode(self.data, validate=True)

    @model_validator(mode="after")
    def _data_matches_hash(self) -> Self:
        try:
            raw = self.decoded()
        except (binascii.Error, ValueError) as exc:
            raise ValueError("font data is not valid base64") from exc
        if len(raw) > MAX_FONT_BYTES:
            raise ValueError(f"font is larger than {MAX_FONT_BYTES // (1024 * 1024)} MB")
        if hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("sha256 does not match the font data")
        return self


class FontRef(_Model):
    """Either a built-in font by ``key`` or an embedded ``custom`` font."""

    key: str | None = None
    custom: CustomFont | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.key is None) == (self.custom is None):
            raise ValueError("font must set exactly one of 'key' or 'custom'")
        return self

    @property
    def cache_id(self) -> str:
        """What identifies the font for hashing and caching."""
        return f"key:{self.key}" if self.custom is None else f"sha256:{self.custom.sha256}"


class ColorRef(_Model):
    """Either a registry ``filament`` id or a literal ``hex`` colour, never both."""

    filament: str | None = None
    hex: str | None = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")

    @model_validator(mode="after")
    def _exactly_one(self) -> Self:
        if (self.filament is None) == (self.hex is None):
            raise ValueError("colour must set exactly one of 'filament' or 'hex'")
        return self


class Colors(_Model):
    relief: ColorRef = Field(default_factory=lambda: ColorRef(filament="local-bambu-pla-silk-gold"))


class TextConfig(_Model):
    text: str = Field("", max_length=MAX_TEXT_LENGTH)
    size: float = Field(26.0, ge=10, le=60)
    letter_spacing: float = Field(1.2, ge=0, le=10)
    radius: float

    @field_validator("text")
    @classmethod
    def _printable(cls, value: str) -> str:
        if not value.isprintable():
            raise ValueError("text may only contain printable characters")
        return value


class Dots(_Model):
    enabled: bool = True
    radius: float = Field(5.0, ge=1, le=10)


class TraceOptions(_Model):
    threshold: int = Field(128, ge=0, le=255)
    simplify: float = Field(0.4, ge=0, le=5)
    drop_largest: bool = False
    inner_disc: float | None = None
    min_area: float = Field(0, ge=0)
    drop_thin_rings: bool = True
    invert: bool = False


class IconSource(_Model):
    """Provenance of a traced icon. Optional and not hashed."""

    filename: str | None = None
    sha256: str | None = None
    trace: TraceOptions | None = None
    data_url: str | None = None


class IconPolygon(_Model):
    exterior: list[Point2D]
    holes: list[list[Point2D]] = Field(default_factory=list)


class IconGeometry(_Model):
    """Traced outline: max radius 100, centred on the origin, Y up."""

    polygons: list[IconPolygon] = Field(min_length=1)
    source: IconSource | None = None

    @model_validator(mode="after")
    def _limits(self) -> Self:
        vertices = 0
        for index, polygon in enumerate(self.polygons):
            for ring in (polygon.exterior, *polygon.holes):
                if len(ring) < 3:
                    raise ValueError(f"polygon {index} has a ring with fewer than 3 points")
                vertices += len(ring)
                for x, y in ring:
                    if not (math.isfinite(x) and math.isfinite(y)):
                        raise ValueError(f"polygon {index} has a non-finite coordinate")
                    if math.hypot(x, y) > ICON_RADIUS + ICON_RADIUS_TOLERANCE:
                        raise ValueError(
                            f"polygon {index} has a point outside radius {ICON_RADIUS:g}"
                        )
        if vertices > MAX_ICON_VERTICES:
            raise ValueError(f"icon has {vertices} vertices, the limit is {MAX_ICON_VERTICES}")
        return self


class IconPlacement(_Model):
    geometry: IconGeometry
    fit: float = Field(0.82, gt=0, le=2.0)
    dx: float = Field(0.0, ge=-R_EDGE, le=R_EDGE)
    dy: float = Field(0.0, ge=-R_EDGE, le=R_EDGE)
    rot: float = Field(0.0, ge=-360, le=360)


def _default_top() -> TextConfig:
    return TextConfig(radius=118.5)


def _default_bottom() -> TextConfig:
    return TextConfig(radius=134.2)


class FaceConfig(_Model):
    inlay: ColorRef = Field(
        default_factory=lambda: ColorRef(filament="local-bambu-pla-matte-dark-blue")
    )
    top_text: TextConfig = Field(default_factory=_default_top)
    bottom_text: TextConfig = Field(default_factory=_default_bottom)
    dots: Dots = Field(default_factory=Dots)
    icon: IconPlacement | None = None


class Faces(_Model):
    front: FaceConfig = Field(default_factory=FaceConfig)
    back: FaceConfig = Field(default_factory=FaceConfig)


class PrintSettings(_Model):
    nozzle_mm: float = Field(0.4, ge=0.1, le=1.2)
    enamel_depth_mm: float = Field(0.4, ge=0.2, le=1.0)


class CoinConfig(_Model):
    schema_version: Literal[1] = SCHEMA_VERSION
    meta: Meta = Field(default_factory=Meta)
    size: Size = Field(default_factory=Size)
    edge: Edge = Field(default_factory=Edge)
    rings: Rings = Field(default_factory=Rings)
    font: FontRef = Field(default_factory=lambda: FontRef(key="poppins-semibold"))
    colors: Colors = Field(default_factory=Colors)
    faces: Faces = Field(default_factory=Faces)
    print: PrintSettings = Field(default_factory=PrintSettings)

    @model_validator(mode="after")
    def _cross_field_rules(self) -> Self:
        rings = self.rings
        if self.edge.style == "reeded" and rings.r_inlay + MIN_RING_GAP > rings.r_edge - (
            self.edge.depth
        ):
            raise ValueError(
                f"rings.r_inlay ({rings.r_inlay:g}) must stay {MIN_RING_GAP:g} units inside "
                f"the reeding (r_edge - edge.depth = {rings.r_edge - self.edge.depth:g})"
            )

        low = rings.r_div_out + TEXT_BAND_MARGIN
        high = rings.r_inlay - TEXT_BAND_MARGIN
        for face_name in ("front", "back"):
            face: FaceConfig = getattr(self.faces, face_name)
            for text_name in ("top_text", "bottom_text"):
                radius = getattr(face, text_name).radius
                if not low <= radius <= high:
                    raise ValueError(
                        f"faces.{face_name}.{text_name}.radius ({radius:g}) must be between "
                        f"r_div_out + {TEXT_BAND_MARGIN:g} ({low:g}) and "
                        f"r_inlay - {TEXT_BAND_MARGIN:g} ({high:g})"
                    )

        if 2 * self.print.enamel_depth_mm + 0.2 > self.size.body_mm + 1e-9:
            raise ValueError(
                "print.enamel_depth_mm is too deep for size.body_mm: the front and back "
                "enamel pockets need at least 0.2 mm of body between them"
            )
        return self

    def face(self, name: FaceName) -> FaceConfig:
        return self.faces.front if name == "front" else self.faces.back

    @property
    def scale(self) -> float:
        """Millimetres per design unit."""
        return self.size.diameter_mm / DESIGN_DIAMETER

    def to_json_dict(self) -> dict:
        """The file/wire form: unset optional branches are omitted, not written as null."""
        data = self.model_dump(mode="json", exclude_none=True)
        for face_name in ("front", "back"):
            data["faces"][face_name].setdefault("icon", None)
        return data
