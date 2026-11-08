"""JSON API consumed by the Vue front end.

Routes stay thin: validation lives in ``app.schemas``, the listings view model
in ``app.views`` and the check routine in ``app.monitor``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app import telegram
from app.config import DEFAULT_NEIGHBORHOODS, KIND_LABELS, SOURCE_LABELS
from app.db import get_session, load_settings
from app.models import Listing, SourceStatus
from app.monitor import is_check_running, run_check
from app.scheduler import apply_schedule
from app.schemas import (
    CardOut,
    FavoritesSummaryOut,
    ListingOut,
    ListingsOut,
    ListingUpdate,
    MessageOut,
    OptionsOut,
    SettingsOut,
    SettingsUpdate,
    SourceStatusOut,
    StatusOut,
    TelegramUpdate,
)
from app.views import SORT_LABELS, ListingFilters, build_listing_cards, neighborhood_options

TELEGRAM_TEST_MESSAGE = (
    "✅ <b>Toca na Lagoa</b> conectado! Você vai receber aqui os apartamentos novos e as novidades dos favoritos."
)

router = APIRouter(prefix="/api")
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/options")
def get_options(session: SessionDep) -> OptionsOut:
    """Labels and suggestions for filters and forms."""
    seen_neighborhoods = session.exec(select(Listing.neighborhood).distinct()).all()
    return OptionsOut(
        source_labels=SOURCE_LABELS,
        kind_labels=KIND_LABELS,
        sort_labels=SORT_LABELS,
        default_neighborhoods=DEFAULT_NEIGHBORHOODS,
        neighborhood_suggestions=sorted(set(DEFAULT_NEIGHBORHOODS) | set(seen_neighborhoods)),
    )


@router.get("/listings")
def get_listings(request: Request, session: SessionDep) -> ListingsOut:
    """Listings matching the filters given as query parameters."""
    filters = ListingFilters.from_query(dict(request.query_params))
    return ListingsOut(
        cards=[CardOut.from_card(card) for card in build_listing_cards(session, filters)],
        neighborhoods=neighborhood_options(session),
    )


@router.patch("/listings/{listing_id}")
def update_listing(listing_id: int, update: ListingUpdate, session: SessionDep) -> ListingOut:
    """Star/unstar or hide/show a listing.

    Starring takes the current price and availability as the reference for
    favorite alerts.
    """
    listing = session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anúncio não encontrado")
    if update.favorite is not None:
        if update.favorite and not listing.favorite:
            listing.start_watching()
        listing.favorite = update.favorite
    if update.hidden is not None:
        listing.hidden = update.hidden
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return ListingOut.from_model(listing)


@router.get("/favorites/summary")
def get_favorites_summary(session: SessionDep) -> FavoritesSummaryOut:
    """Count favorites still listed and favorites that left the portals."""
    availability = session.exec(select(Listing.active).where(Listing.favorite)).all()
    available = sum(availability)
    return FavoritesSummaryOut(available=available, gone=len(availability) - available)


@router.get("/status")
def get_status(session: SessionDep) -> StatusOut:
    """Latest check outcome per portal and whether a check is running now."""
    return _status(session)


@router.post("/check")
async def check_now(session: SessionDep) -> StatusOut:
    """Run a check immediately and return the new status."""
    await run_check()
    session.expire_all()
    return _status(session)


def _status(session: Session) -> StatusOut:
    """Assemble the monitor status."""
    settings = load_settings(session)
    statuses = session.exec(select(SourceStatus).order_by(SourceStatus.source)).all()
    return StatusOut(
        last_check_at=settings.last_check_at,
        last_check_status=settings.last_check_status,
        running=is_check_running(),
        sources=[SourceStatusOut.from_model(source_status) for source_status in statuses],
    )


@router.get("/settings")
def get_settings(session: SessionDep) -> SettingsOut:
    """Current search, schedule and Telegram settings."""
    return SettingsOut.from_model(load_settings(session))


@router.put("/settings")
def update_settings(update: SettingsUpdate, session: SessionDep) -> SettingsOut:
    """Persist the search settings and reschedule checks."""
    settings = load_settings(session)
    settings.enabled = update.enabled
    settings.check_times = ",".join(update.check_times)
    settings.neighborhoods = ",".join(update.neighborhoods)
    settings.max_bedrooms = update.max_bedrooms
    settings.max_area = update.max_area
    settings.min_total = update.min_total
    settings.max_total = update.max_total
    session.add(settings)
    session.commit()
    apply_schedule(settings)
    return SettingsOut.from_model(settings)


@router.put("/telegram")
def update_telegram(update: TelegramUpdate, session: SessionDep) -> SettingsOut:
    """Save Telegram credentials; a blank token keeps the current one."""
    settings = load_settings(session)
    if update.bot_token.strip():
        settings.telegram_bot_token = update.bot_token.strip()
    settings.telegram_chat_id = update.chat_id.strip()
    session.add(settings)
    session.commit()
    return SettingsOut.from_model(settings)


@router.post("/telegram/detect")
async def detect_telegram_chat(session: SessionDep) -> SettingsOut:
    """Fill the chat id from the latest message sent to the bot."""
    settings = load_settings(session)
    try:
        detected = await telegram.detect_chat_id(settings.telegram_bot_token)
    except telegram.TelegramError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Telegram: {error}") from error
    if detected is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Nenhuma mensagem encontrada. Envie /start para o bot e tente de novo.",
        )
    settings.telegram_chat_id, _ = detected
    session.add(settings)
    session.commit()
    return SettingsOut.from_model(settings)


@router.post("/telegram/test")
async def test_telegram(session: SessionDep) -> MessageOut:
    """Send a test message to the configured chat."""
    settings = load_settings(session)
    try:
        await telegram.send_message(settings.telegram_bot_token, settings.telegram_chat_id, TELEGRAM_TEST_MESSAGE)
    except telegram.TelegramError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Telegram: {error}") from error
    return MessageOut(message="Mensagem de teste enviada")
