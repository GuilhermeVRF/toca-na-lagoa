"""Check routine: fetch every source, update the stored listings and send alerts."""

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from sqlmodel import Session, col, select

from app import telegram
from app.browser_http import browser_client
from app.config import KIND_LABELS, REQUEST_TIMEOUT_SECONDS, SOURCE_LABELS, TIMEZONE
from app.db import engine, load_settings
from app.dedup import GroupCandidate, are_same_apartment, assign_groups
from app.models import Listing, PriceHistory, Settings, SourceStatus
from app.normalize import canonical_neighborhood, format_brl, matches_criteria
from app.sources.base import FoundListing, SearchCriteria, Source, SourceError
from app.sources.registry import all_sources

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 3800

_check_lock = asyncio.Lock()


@dataclass
class CheckResult:
    """Summary of a check run, shown in the UI."""

    found: int = 0
    new: int = 0
    favorite_updates: int = 0
    alerts_sent: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def status_text(self) -> str:
        """Short Portuguese status line for the dashboard."""
        text = (
            f"{self.found} anúncios encontrados, {self.new} novos, "
            f"{self.favorite_updates} novidades nos favoritos, {self.alerts_sent} alertas enviados"
        )
        if self.errors:
            text += f" · {len(self.errors)} erro(s): {self.errors[0]}"
        return text


@dataclass
class Alert:
    """A listing worth telling the user about.

    For favorite updates, ``previous_total`` / ``previous_active`` hold what the
    user was last told, and ``still_listed_on`` the portals where a copy of a
    retired favorite is still active.
    """

    listing: Listing
    previous_total: int | None = None
    previous_active: bool | None = None
    still_listed_on: list[str] = field(default_factory=list)


def is_check_running() -> bool:
    """Whether a check (scheduled or manual) is in progress."""
    return _check_lock.locked()


async def run_check(sources: list[Source] | None = None) -> CheckResult:
    """Run a full check of every source.

    Concurrent calls (scheduler + "check now" button) are serialized.

    Args:
        sources: Sources to fetch; defaults to all of them (tests pass fakes).

    Returns:
        Summary of what was found and alerted.
    """
    async with _check_lock:
        with Session(engine) as session:
            settings = load_settings(session)
            now = datetime.now(TIMEZONE).replace(tzinfo=None)
            result = CheckResult()
            found_by_source = await _fetch_all(sources or all_sources(), _criteria(settings), session, now, result)
            new_ids = _store_listings(session, found_by_source, now)
            result.new = len(new_ids)
            _regroup(session)
            await _alert(session, settings, result)
            if found_by_source:
                settings.initial_sync_done = True
            settings.last_check_at = now
            settings.last_check_status = result.status_text
            session.add(settings)
            session.commit()
            logger.info("Check finished: %s", result.status_text)
            return result


def _criteria(settings: Settings) -> SearchCriteria:
    """Search criteria from the user's settings."""
    return SearchCriteria(
        neighborhoods=settings.neighborhood_list,
        max_bedrooms=settings.max_bedrooms,
        max_area=settings.max_area,
        min_total=settings.min_total,
        max_total=settings.max_total,
    )


async def _fetch_all(
    sources: list[Source],
    criteria: SearchCriteria,
    session: Session,
    now: datetime,
    result: CheckResult,
) -> dict[str, list[FoundListing]]:
    """Fetch every source, keeping matching listings; failed sources are left out.

    Favorites are kept even when they no longer match (e.g. the price rose above
    the range), so they keep being followed instead of being retired as gone.
    """
    found_by_source: dict[str, list[FoundListing]] = {}
    async with browser_client(REQUEST_TIMEOUT_SECONDS) as client:
        for source in sources:
            status = session.get(SourceStatus, source.name) or SourceStatus(source=source.name)
            status.last_run_at = now
            try:
                fetched = await source.fetch(client, criteria)
            except SourceError as error:
                logger.warning("Source %s failed: %s", source.name, error)
                result.errors.append(str(error))
                status.ok, status.error = False, str(error)
                session.add(status)
                continue
            except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
                # A portal can change its JSON shape while still returning HTTP 200.
                # Treat expected parsing failures like a source outage so the rest of
                # the check can continue and listings from this source are not retired.
                label = SOURCE_LABELS.get(source.name, source.name)
                message = f"{label}: resposta inválida ({error.__class__.__name__})"
                logger.warning("Source %s returned malformed data: %r", source.name, error)
                result.errors.append(message)
                status.ok, status.error = False, message
                session.add(status)
                continue
            favorite_ids = _favorite_ids(session, source.name)
            matching = _unique(listing for listing in fetched if matches_criteria(listing, criteria))
            kept_favorites = _unique(
                listing
                for listing in fetched
                if listing.external_id in favorite_ids and not matches_criteria(listing, criteria)
            )
            for listing in matching + kept_favorites:
                listing.neighborhood = canonical_neighborhood(listing, criteria.neighborhoods)
            found_by_source[source.name] = matching + kept_favorites
            result.found += len(matching)
            status.ok, status.error, status.found = True, "", len(matching)
            session.add(status)
    return found_by_source


def _favorite_ids(session: Session, source_name: str) -> set[str]:
    """External ids of the user's favorites on one source."""
    return set(
        session.exec(select(Listing.external_id).where(Listing.source == source_name, Listing.favorite)).all(),
    )


def _unique(listings: Iterable[FoundListing]) -> list[FoundListing]:
    """Drop repeated external ids (a listing can show up under two neighborhood searches)."""
    return list({listing.external_id: listing for listing in listings}.values())


def _store_listings(
    session: Session,
    found_by_source: dict[str, list[FoundListing]],
    now: datetime,
) -> list[int]:
    """Insert or update listings, record price changes and retire listings that disappeared.

    Returns:
        Ids of listings seen for the first time.
    """
    new_ids: list[int] = []
    for source_name, found in found_by_source.items():
        stored = {
            listing.external_id: listing
            for listing in session.exec(select(Listing).where(Listing.source == source_name)).all()
        }
        for item in found:
            existing = stored.pop(item.external_id, None)
            if existing is None:
                new_ids.append(_insert(session, item, now))
            else:
                _update(session, existing, item, now)
        for missing in stored.values():
            missing.active = False
            session.add(missing)
    session.flush()
    return new_ids


def _insert(session: Session, item: FoundListing, now: datetime) -> int:
    """Store a listing seen for the first time, with its first price point."""
    listing = Listing(
        **_listing_fields(item),
        source=item.source,
        external_id=item.external_id,
        first_seen=now,
        last_seen=now,
    )
    session.add(listing)
    session.flush()
    session.add(PriceHistory(listing_id=listing.id, observed_at=now, total=listing.total))
    return listing.id


def _update(session: Session, listing: Listing, item: FoundListing, now: datetime) -> None:
    """Refresh a known listing, recording a price point when the total changed."""
    previous_total = listing.total
    for name, value in _listing_fields(item).items():
        setattr(listing, name, value)
    listing.last_seen = now
    listing.active = True
    if listing.total != previous_total:
        session.add(PriceHistory(listing_id=listing.id, observed_at=now, total=listing.total))
    session.add(listing)


def _listing_fields(item: FoundListing) -> dict:
    """Columns copied from a fetched listing on every check."""
    return {
        "url": item.url,
        "title": item.title,
        "kind": item.kind or "apartment",
        "bedrooms": item.bedrooms,
        "area": item.area,
        "rent": item.rent,
        "condo": item.condo,
        "iptu": item.iptu,
        "total": item.total,
        "neighborhood": item.neighborhood,
        "address": item.address,
        "image_url": item.image_url,
        "furnished": item.furnished,
    }


def _regroup(session: Session) -> None:
    """Recompute which active listings are the same apartment on different portals."""
    active = session.exec(select(Listing).where(Listing.active)).all()
    groups = assign_groups([_group_candidate(listing) for listing in active])
    for listing in active:
        if listing.group_id != groups[listing.id]:
            listing.group_id = groups[listing.id]
            session.add(listing)
    session.flush()


def _group_candidate(listing: Listing) -> GroupCandidate:
    """The fields of a listing used to match it with copies on other portals."""
    return GroupCandidate(
        listing_id=listing.id,
        source=listing.source,
        neighborhood=listing.neighborhood,
        area=listing.area,
        price=listing.rent,
    )


async def _alert(session: Session, settings: Settings, result: CheckResult) -> None:
    """Find new listings and favorite updates, send them to Telegram and mark them as delivered.

    The first check only fills the database. Undelivered alerts stay pending and
    are retried on the next check; without Telegram configured they are dropped.
    """
    new_alerts = _pending_new(session)
    favorite_alerts = _pending_favorite_updates(session)
    result.favorite_updates = len(favorite_alerts)
    if not settings.initial_sync_done:
        _mark_delivered(session, new_alerts + favorite_alerts)
        return
    if not (new_alerts or favorite_alerts):
        return
    if not settings.telegram_configured:
        _mark_delivered(session, new_alerts + favorite_alerts)
        return
    try:
        for message in format_alert_messages(new_alerts, favorite_alerts):
            await telegram.send_message(settings.telegram_bot_token, settings.telegram_chat_id, message)
    except telegram.TelegramError as error:
        result.errors.append(f"Telegram: {error}")
        return
    _mark_delivered(session, new_alerts + favorite_alerts)
    result.alerts_sent = len(new_alerts) + len(favorite_alerts)


def _pending_new(session: Session) -> list[Alert]:
    """Visible, never-notified listings, one per apartment group.

    A cross-posted copy of an apartment that was already notified is marked as
    notified silently.
    """
    candidates = session.exec(
        select(Listing)
        .where(Listing.active, col(Listing.hidden).is_(False), col(Listing.notified).is_(False))
        .order_by(col(Listing.total)),
    ).all()
    notified_groups = set(
        session.exec(
            select(Listing.group_id).where(col(Listing.group_id).is_not(None), Listing.notified),
        ).all(),
    )
    alerts: list[Alert] = []
    for listing in candidates:
        if listing.group_id is not None and listing.group_id in notified_groups:
            listing.notified = True
            session.add(listing)
            continue
        if listing.group_id is not None:
            notified_groups.add(listing.group_id)
        alerts.append(Alert(listing=listing))
    return alerts


def _pending_favorite_updates(session: Session) -> list[Alert]:
    """Favorites whose price or availability changed since the user was last told.

    A favorite with no reference yet (starred before this feature existed) starts being watched
    silently.
    """
    favorites = session.exec(select(Listing).where(Listing.favorite)).all()
    alerts: list[Alert] = []
    for listing in favorites:
        if listing.watched_total is None or listing.watched_active is None:
            listing.start_watching()
            session.add(listing)
            continue
        if listing.watched_total == listing.total and listing.watched_active == listing.active:
            continue
        alerts.append(
            Alert(
                listing=listing,
                previous_total=listing.watched_total,
                previous_active=listing.watched_active,
                still_listed_on=[] if listing.active else _active_copies(session, listing),
            ),
        )
    return alerts


def _active_copies(session: Session, listing: Listing) -> list[str]:
    """Portals where the same apartment is still listed.

    Compared directly instead of by ``group_id``, since regrouping only covers
    active listings and a retired one keeps a stale group.
    """
    retired = _group_candidate(listing)
    others = session.exec(
        select(Listing).where(
            Listing.active,
            Listing.source != listing.source,
            Listing.neighborhood == listing.neighborhood,
        ),
    ).all()
    return sorted(
        {
            SOURCE_LABELS.get(other.source, other.source)
            for other in others
            if are_same_apartment(retired, _group_candidate(other))
        },
    )


def _mark_delivered(session: Session, alerts: list[Alert]) -> None:
    """Record that these alerts reached the user (or never will), so they are not repeated."""
    for alert in alerts:
        alert.listing.notified = True
        if alert.listing.favorite:
            alert.listing.start_watching()
        session.add(alert.listing)


def format_alert_messages(new_alerts: list[Alert], favorite_alerts: list[Alert]) -> list[str]:
    """Build Telegram HTML messages, split to stay under Telegram's length limit."""
    blocks: list[str] = []
    if favorite_alerts:
        blocks.append(f"⭐ <b>{len(favorite_alerts)} novidade(s) nos favoritos</b>")
        blocks.extend(_format_favorite_update(alert) for alert in favorite_alerts)
    if new_alerts:
        blocks.append(f"🏠 <b>{len(new_alerts)} apartamento(s) novo(s) na Pampulha</b>")
        blocks.extend(_format_listing(alert) for alert in new_alerts)

    messages: list[str] = []
    current = ""
    for block in blocks:
        if current and len(current) + len(block) + 2 > MAX_MESSAGE_LENGTH:
            messages.append(current)
            current = ""
        current = f"{current}\n\n{block}" if current else block
    if current:
        messages.append(current)
    return messages


def _format_listing(alert: Alert) -> str:
    """Format one new-listing entry of an alert message."""
    listing = alert.listing
    kind = KIND_LABELS.get(listing.kind, "Apartamento")
    price = f"<b>{format_brl(listing.total)}</b>/mês"
    details = [f"aluguel {format_brl(listing.rent)}"]
    if listing.area:
        details.append(f"{listing.area} m²")
    if listing.furnished:
        details.append("mobiliado")
    source = SOURCE_LABELS.get(listing.source, listing.source)
    return (
        f"<b>{escape(kind)} · {escape(listing.neighborhood)}</b>\n"
        f"💰 {price}\n"
        f"{' · '.join(details)}\n"
        f'<a href="{escape(listing.url)}">Ver no {source}</a>'
    )


def _format_favorite_update(alert: Alert) -> str:
    """Format what changed on a favorite: it left the portal, came back, or changed price."""
    listing = alert.listing
    kind = KIND_LABELS.get(listing.kind, "Apartamento")
    source = SOURCE_LABELS.get(listing.source, listing.source)
    lines = [f"<b>{escape(kind)} · {escape(listing.neighborhood)}</b>"]
    if not listing.active and alert.previous_active:
        lines.append(f"🚫 Saiu do ar no {source} — provavelmente foi alugado")
        if alert.still_listed_on:
            lines.append(f"Ainda anunciado no {escape(', '.join(alert.still_listed_on))}")
    elif listing.active and alert.previous_active is False:
        lines.append(f"✅ Voltou a ser anunciado no {source}")
    if alert.previous_total is not None and alert.previous_total != listing.total:
        change = (listing.total - alert.previous_total) / alert.previous_total * 100
        icon = "📉" if change < 0 else "📈"
        lines.append(
            f"{icon} <s>{format_brl(alert.previous_total)}</s> → <b>{format_brl(listing.total)}</b>/mês "
            f"({change:+.0f}%)".replace("-", "−"),
        )
    else:
        lines.append(f"💰 <b>{format_brl(listing.total)}</b>/mês")
    lines.append(f'<a href="{escape(listing.url)}">Ver no {source}</a>')
    return "\n".join(lines)
