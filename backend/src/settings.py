"""Application settings.

One Settings class, lowercase fields with local-friendly defaults so the app runs
with no environment variables. Environment variables match case-insensitively; a
``.env`` file in ``backend/`` is read in dev.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["dev", "test", "preview", "prod"] = "dev"
    version: str = "0.1.0"

    # HTTP
    cors_origins: str = "http://localhost:5173"

    # Geometry builds (used from phase 1 onwards)
    build_workers: int = 2
    build_timeout_s: float = 20
    cache_size_mb: int = 256
    max_json_bytes: int = 2 * 1024 * 1024

    # Uploads and complexity limits (decision D14 / D18)
    max_upload_bytes: int = 10 * 1024 * 1024
    max_icon_vertices: int = 50_000
    max_font_bytes: int = 2 * 1024 * 1024

    # Contact flow (decision D19). Without smtp_host the mail is only logged.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "coins@danielvdspoel.com"
    contact_to: str = "contact@danielvdspoel.nl"
    contact_min_seconds: float = 3.0
    contact_rate_limit: int = 3
    """Contact requests per client IP per ``contact_rate_window_s``, per pod."""
    contact_rate_window_s: float = 600.0
    # Concurrent requests per client IP (per pod). Previews cover GLB, stats and
    # icon traces; 3 leaves room for a request the browser already abandoned.
    client_max_exports: int = 1
    client_max_previews: int = 3

    # Data locations
    fonts_dir: Path = BACKEND_DIR / "fonts"
    data_dir: Path = BACKEND_DIR / "data"

    # Filament colours (decision D5). 0 hours disables the network: the committed
    # snapshot is served as is, which is what tests and offline dev want.
    filamentcolors_url: str = "https://filamentcolors.xyz"
    filamentcolors_refresh_hours: float = 0
    filamentcolors_timeout_s: float = 10

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def allow_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
