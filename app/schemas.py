"""Request and response models of the JSON API.

Validation messages are user-facing, so they are written in Portuguese.
"""

import re

from pydantic import BaseModel, NaiveDatetime, field_validator, model_validator

from app.config import SOURCE_LABELS
from app.models import Listing, PriceHistory, Settings, SourceStatus
from app.views import ListingCard

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ListingOut(BaseModel):
    """A listing as shown on a card."""

    id: int
    source: str
    url: str
    title: str
    kind: str
    bedrooms: int
    area: int | None
    rent: int
    condo: int
    iptu: int
    total: int
    neighborhood: str
    address: str
    image_url: str
    furnished: bool | None
    first_seen: NaiveDatetime
    last_seen: NaiveDatetime
    active: bool
    favorite: bool
    hidden: bool

    @classmethod
    def from_model(cls, listing: Listing) -> "ListingOut":
        """Build from the database row."""
        return cls.model_validate(listing, from_attributes=True)


class CopyOut(BaseModel):
    """The same apartment advertised on another portal."""

    source: str
    url: str
    total: int


class PricePointOut(BaseModel):
    """One observed total price."""

    observed_at: NaiveDatetime
    total: int


class CardOut(BaseModel):
    """One apartment on the listings page, with its copies and price history."""

    listing: ListingOut
    copies: list[CopyOut]
    history: list[PricePointOut]
    is_new: bool
    price_per_m2: float | None
    previous_total: int | None

    @classmethod
    def from_card(cls, card: ListingCard) -> "CardOut":
        """Build from the view model assembled by ``app.views``."""
        return cls(
            listing=ListingOut.from_model(card.listing),
            copies=[CopyOut(source=copy.source, url=copy.url, total=copy.total) for copy in card.copies],
            history=[_price_point(point) for point in card.history],
            is_new=card.is_new,
            price_per_m2=card.price_per_m2,
            previous_total=card.previous_total,
        )


def _price_point(point: PriceHistory) -> PricePointOut:
    """Convert a price history row."""
    return PricePointOut(observed_at=point.observed_at, total=point.total)


class ListingsOut(BaseModel):
    """The listings page content for the requested filters."""

    cards: list[CardOut]
    neighborhoods: list[str]


class ListingUpdate(BaseModel):
    """Flags the user can toggle on a listing; omitted fields are left unchanged."""

    favorite: bool | None = None
    hidden: bool | None = None


class SourceStatusOut(BaseModel):
    """Outcome of the latest fetch from one portal."""

    source: str
    label: str
    ok: bool
    found: int
    error: str

    @classmethod
    def from_model(cls, status: SourceStatus) -> "SourceStatusOut":
        """Build from the database row."""
        return cls(
            source=status.source,
            label=SOURCE_LABELS.get(status.source, status.source),
            ok=status.ok,
            found=status.found,
            error=status.error,
        )


class StatusOut(BaseModel):
    """Monitor status, polled by the UI to refresh itself after scheduled checks."""

    last_check_at: NaiveDatetime | None
    last_check_status: str
    running: bool
    sources: list[SourceStatusOut]


class SettingsOut(BaseModel):
    """Search and alert settings; the bot token itself is never sent back."""

    enabled: bool
    check_times: list[str]
    neighborhoods: list[str]
    max_bedrooms: int
    max_area: int | None
    min_total: int | None
    max_total: int | None
    telegram_token_set: bool
    telegram_chat_id: str
    telegram_configured: bool

    @classmethod
    def from_model(cls, settings: Settings) -> "SettingsOut":
        """Build from the settings row."""
        return cls(
            enabled=settings.enabled,
            check_times=settings.check_time_list,
            neighborhoods=settings.neighborhood_list,
            max_bedrooms=settings.max_bedrooms,
            max_area=settings.max_area,
            min_total=settings.min_total,
            max_total=settings.max_total,
            telegram_token_set=bool(settings.telegram_bot_token),
            telegram_chat_id=settings.telegram_chat_id,
            telegram_configured=settings.telegram_configured,
        )


class SettingsUpdate(BaseModel):
    """Search settings submitted from the settings page."""

    enabled: bool
    check_times: list[str]
    neighborhoods: list[str]
    max_bedrooms: int
    max_area: int | None = None
    min_total: int | None = None
    max_total: int | None = None

    @field_validator("check_times")
    @classmethod
    def _valid_times(cls, times: list[str]) -> list[str]:
        cleaned = sorted({time.strip() for time in times if time.strip()})
        if not cleaned or not all(TIME_PATTERN.match(time) for time in cleaned):
            raise ValueError("Horários de verificação inválidos")
        return cleaned

    @field_validator("neighborhoods")
    @classmethod
    def _at_least_one_neighborhood(cls, names: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(" ".join(name.split()) for name in names if name.strip()))
        if not cleaned:
            raise ValueError("Informe pelo menos um bairro")
        if any("," in name for name in cleaned):
            raise ValueError("Nome de bairro não pode conter vírgula")
        return cleaned

    @field_validator("max_bedrooms")
    @classmethod
    def _bedrooms_in_range(cls, bedrooms: int) -> int:
        if not 0 <= bedrooms <= 5:
            raise ValueError("Máximo de quartos deve ficar entre 0 e 5")
        return bedrooms

    @field_validator("max_area", "min_total", "max_total")
    @classmethod
    def _positive_or_blank(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("Use um valor positivo ou deixe em branco")
        return value

    @model_validator(mode="after")
    def _min_not_above_max(self) -> "SettingsUpdate":
        if self.min_total is not None and self.max_total is not None and self.min_total > self.max_total:
            raise ValueError("O valor mínimo é maior que o máximo")
        return self


class TelegramUpdate(BaseModel):
    """Telegram credentials; a blank token keeps the saved one."""

    bot_token: str = ""
    chat_id: str = ""


class FavoritesSummaryOut(BaseModel):
    """How many favorites are still listed and how many left the portals."""

    available: int
    gone: int


class OptionsOut(BaseModel):
    """Labels and choices the UI needs to render filters and forms."""

    source_labels: dict[str, str]
    kind_labels: dict[str, str]
    sort_labels: dict[str, str]
    default_neighborhoods: list[str]
    neighborhood_suggestions: list[str]


class MessageOut(BaseModel):
    """A short user-facing confirmation."""

    message: str
