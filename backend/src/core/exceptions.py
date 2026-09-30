"""Domain exceptions. The API layer translates these to HTTP in phase 2."""


class CoinError(Exception):
    """Base class for everything the domain raises on purpose."""


class InvalidConfig(CoinError):
    """The config is structurally or semantically invalid (user error).

    ``errors`` holds ``{"loc": [...], "msg": "...", "code": "..."}`` entries, the
    same shape the API returns.
    """

    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or [{"loc": [], "msg": message, "code": "invalid_config"}]


class InvalidFont(CoinError):
    """A font file could not be parsed or has no usable outlines."""


class UnknownFilament(InvalidConfig):
    """A colour references a filament id the registry does not know."""


class NotWatertight(CoinError):
    """A built solid is not a closed volume. Always a bug, never user error."""


class IconTraceFailed(CoinError):
    """An image could not be traced into usable icon geometry."""


class BuildTimeout(CoinError):
    """A build did not finish within the configured time."""


class MailerError(CoinError):
    """The contact email could not be sent."""


class PayloadTooLarge(CoinError):
    """An upload or request body exceeds the configured limit."""
