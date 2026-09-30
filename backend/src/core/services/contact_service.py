"""The "don't have a printer?" flow (decision D19): one email, nothing stored."""

import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.core.config.models import CoinConfig
from src.core.engine.quality import PREVIEW
from src.core.engine.svg import face_svg
from src.core.exceptions import InvalidConfig
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.interfaces.mailer import Attachment, Mailer
from src.core.services.coin_service import slugify
from src.core.services.colors import resolve_colors
from src.core.services.validation_service import ValidationService
from src.core.tools.rate_limit import SlidingWindowLimiter


class ContactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str = Field("", max_length=4000)
    attach_design: bool = False
    config: CoinConfig | None = None
    honeypot: str = ""
    elapsed_s: float = Field(
        ge=0,
        description="Seconds the form was open, measured by the browser. A duration, "
        "not a timestamp, so a visitor's clock being off does not matter.",
    )


@dataclass(frozen=True)
class ContactSettings:
    to: str
    min_seconds: float


class ContactService:
    def __init__(
        self,
        mailer: Mailer,
        fonts: FontRegistry,
        filaments: FilamentRegistry,
        settings: ContactSettings,
        validation: ValidationService,
        limiter: SlidingWindowLimiter,
    ) -> None:
        self._mailer = mailer
        self._fonts = fonts
        self._filaments = filaments
        self._settings = settings
        self._validation = validation
        self._limiter = limiter

    def send(self, request: ContactRequest, client: str = "unknown") -> None:
        """Check the anti-spam rules and send.

        Raises ``InvalidConfig`` for bots and ``RateLimited`` when ``client`` sent
        too many requests. An attached design is validated, and its printability
        warnings go into the email so problems show up before printing.
        """
        if request.honeypot:
            raise InvalidConfig(
                "request rejected",
                [{"loc": ["honeypot"], "msg": "must be empty", "code": "spam"}],
            )
        if request.elapsed_s < self._settings.min_seconds:
            raise InvalidConfig(
                "request rejected",
                [{"loc": ["elapsed_s"], "msg": "form submitted too quickly", "code": "spam"}],
            )
        if request.attach_design and request.config is None:
            raise InvalidConfig(
                "attach_design needs a config",
                [
                    {
                        "loc": ["config"],
                        "msg": "required when attach_design is true",
                        "code": "missing",
                    }
                ],
            )

        attachments: list[Attachment] = []
        lines = [
            f"Name: {request.name}",
            f"Email: {request.email}",
            "",
            request.message or "(no message)",
        ]
        if request.attach_design and request.config is not None:
            config = request.config
            slug = slugify(config.meta.name, "design")
            attachments.append(
                Attachment(
                    f"{slug}.coin.json",
                    json.dumps(config.to_json_dict(), indent=1).encode("utf-8"),
                    "application/json",
                )
            )
            glyphs = self._fonts.glyphs(config.font)
            colors = resolve_colors(config, self._filaments)
            svg = face_svg(config, "front", glyphs, colors, PREVIEW)
            attachments.append(
                Attachment(f"{slug}-front.svg", svg.encode("utf-8"), "image/svg+xml")
            )
            lines += [
                "",
                f"Design: {config.meta.name or 'untitled'}, {config.size.diameter_mm:g} mm, "
                f"{config.edge.style} edge",
            ]
            warnings = self._validation.validate(config)
            lines += ["", "Printability:"]
            lines += [f"- {w.severity}: {w.path}: {w.msg}" for w in warnings] or ["- no warnings"]
        self._limiter.hit(client)
        subject = f"Coin print request from {request.name}"
        self._mailer.send(self._settings.to, subject, "\n".join(lines), attachments)
