"""Tests for the check routine: storing listings, price history and alerts."""

from dataclasses import replace

import pytest
from sqlmodel import Session, select

from app import monitor, telegram
from app.db import engine, load_settings
from app.models import Listing, PriceHistory, SourceStatus
from app.sources.base import FoundListing, SearchCriteria, SourceError


class FakeSource:
    """Source returning a fixed list, or raising when ``error`` is set."""

    def __init__(self, name: str, listings: list[FoundListing], error: str = "") -> None:
        self.name = name
        self.listings = listings
        self.error = error

    async def fetch(self, client, criteria: SearchCriteria) -> list[FoundListing]:
        if self.error:
            raise SourceError(self.error)
        return self.listings


def found(external_id: str, rent: int = 1500, source: str = "zap", **overrides) -> FoundListing:
    """A listing that matches the default settings (São Luiz, 1 bedroom, 40 m²)."""
    fields = {
        "source": source,
        "external_id": external_id,
        "url": f"https://example.com/{source}/{external_id}",
        "title": "Apto",
        "kind": "apartment",
        "bedrooms": 1,
        "area": 40,
        "rent": rent,
        "condo": 0,
        "iptu": 0,
        "neighborhood": "São Luiz",
    }
    return FoundListing(**(fields | overrides))


@pytest.fixture
def sent_messages(monkeypatch) -> list[str]:
    """Capture Telegram messages instead of sending them, with Telegram configured."""
    messages: list[str] = []

    async def fake_send(bot_token: str, chat_id: str, html_text: str, link_preview: bool = False) -> None:
        messages.append(html_text)

    monkeypatch.setattr(telegram, "send_message", fake_send)
    return messages


@pytest.fixture
def telegram_configured(session):
    """Configure fake Telegram credentials."""
    settings = load_settings(session)
    settings.telegram_bot_token = "token"
    settings.telegram_chat_id = "chat"
    session.add(settings)
    session.commit()


def all_listings() -> list[Listing]:
    """Every stored listing, read in a fresh session."""
    with Session(engine) as db_session:
        return list(db_session.exec(select(Listing).order_by(Listing.external_id)).all())


async def test_should_not_alert_on_first_check(session, telegram_configured, sent_messages):
    result = await monitor.run_check([FakeSource("zap", [found("1"), found("2")])])
    assert result.new == 2
    assert sent_messages == []
    assert all(listing.notified for listing in all_listings())


async def test_should_alert_only_new_listings_after_first_check(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", [found("1")])])
    result = await monitor.run_check([FakeSource("zap", [found("1"), found("2", rent=1400)])])
    assert result.alerts_sent == 1
    assert len(sent_messages) == 1
    assert "example.com/zap/2" in sent_messages[0]
    assert "example.com/zap/1" not in sent_messages[0]


async def test_should_not_repeat_alert_for_known_listing(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", [])])
    await monitor.run_check([FakeSource("zap", [found("1")])])
    await monitor.run_check([FakeSource("zap", [found("1")])])
    assert len(sent_messages) == 1


async def test_should_drop_listings_outside_criteria(session):
    await monitor.run_check(
        [FakeSource("zap", [found("1"), found("2", bedrooms=3), found("3", neighborhood="Savassi")])],
    )
    assert [listing.external_id for listing in all_listings()] == ["1"]


async def test_should_record_price_history_only_on_change(session):
    await monitor.run_check([FakeSource("zap", [found("1", rent=1500)])])
    await monitor.run_check([FakeSource("zap", [found("1", rent=1500)])])
    await monitor.run_check([FakeSource("zap", [found("1", rent=1300)])])
    totals = session.exec(select(PriceHistory.total).order_by(PriceHistory.id)).all()
    assert totals == [1500, 1300]


def favorite(external_id: str, source: str = "zap") -> None:
    """Star a stored listing the way the UI does."""
    with Session(engine) as db_session:
        listing = db_session.exec(
            select(Listing).where(Listing.source == source, Listing.external_id == external_id),
        ).one()
        listing.favorite = True
        listing.start_watching()
        db_session.add(listing)
        db_session.commit()


async def test_should_alert_when_favorite_leaves_the_portal(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", [found("1"), found("2")])])
    favorite("1")
    result = await monitor.run_check([FakeSource("zap", [found("2")])])
    assert result.favorite_updates == 1
    assert "Saiu do ar" in sent_messages[0]
    assert "example.com/zap/1" in sent_messages[0]


async def test_should_alert_favorite_price_change_in_both_directions(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", [found("1", rent=2000)])])
    favorite("1")
    await monitor.run_check([FakeSource("zap", [found("1", rent=1980)])])
    await monitor.run_check([FakeSource("zap", [found("1", rent=2100)])])
    assert len(sent_messages) == 2
    assert "📉" in sent_messages[0]
    assert "📈" in sent_messages[1]


async def test_should_alert_favorite_coming_back_once(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", [found("1")])])
    favorite("1")
    await monitor.run_check([FakeSource("zap", [])])
    await monitor.run_check([FakeSource("zap", [found("1")])])
    await monitor.run_check([FakeSource("zap", [found("1")])])
    assert len(sent_messages) == 2
    assert "Voltou" in sent_messages[1]


async def test_should_mention_portals_still_listing_a_retired_favorite(session, telegram_configured, sent_messages):
    listing = found("1", rent=1500)
    copy = replace(listing, source="vivareal", rent=1520)
    await monitor.run_check([FakeSource("zap", [listing]), FakeSource("vivareal", [copy])])
    favorite("1")
    await monitor.run_check([FakeSource("zap", []), FakeSource("vivareal", [copy])])
    assert "Ainda anunciado no VivaReal" in sent_messages[0]


async def test_should_not_alert_unchanged_or_non_favorite_listings(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", [found("1", rent=2000), found("2", rent=2000)])])
    favorite("1")
    result = await monitor.run_check([FakeSource("zap", [found("1", rent=2000), found("2", rent=1500)])])
    assert result.favorite_updates == 0
    assert sent_messages == []


async def test_should_keep_only_listings_inside_price_range(session):
    settings = load_settings(session)
    settings.min_total = 1000
    settings.max_total = 1500
    session.add(settings)
    session.commit()
    result = await monitor.run_check(
        [FakeSource("zap", [found("cheap", rent=800), found("fits", rent=1400), found("pricey", rent=2500)])],
    )
    assert result.found == 1
    assert [listing.external_id for listing in all_listings()] == ["fits"]


async def test_should_follow_favorite_priced_out_of_range(session, telegram_configured, sent_messages):
    settings = load_settings(session)
    settings.max_total = 2000
    session.add(settings)
    session.commit()
    await monitor.run_check([FakeSource("zap", [found("1", rent=1800)])])
    favorite("1")
    await monitor.run_check([FakeSource("zap", [found("1", rent=2200)])])
    assert all_listings()[0].active
    assert "📈" in sent_messages[0]
    assert "Saiu do ar" not in sent_messages[0]


async def test_should_skip_listings_above_max_total(session):
    settings = load_settings(session)
    settings.max_total = 2000
    session.add(settings)
    session.commit()
    result = await monitor.run_check([FakeSource("zap", [found("cheap", rent=1400), found("pricey", rent=2500)])])
    assert result.found == 1
    assert [listing.external_id for listing in all_listings()] == ["cheap"]


async def test_should_retire_missing_listings_only_from_successful_sources(session):
    await monitor.run_check(
        [FakeSource("zap", [found("1")]), FakeSource("netimoveis", [found("9", source="netimoveis", area=60)])],
    )
    result = await monitor.run_check(
        [FakeSource("zap", []), FakeSource("netimoveis", [], error="Netimóveis: ReadTimeout")],
    )
    active = {listing.external_id: listing.active for listing in all_listings()}
    assert active == {"1": False, "9": True}
    assert result.errors == ["Netimóveis: ReadTimeout"]
    assert session.get(SourceStatus, "netimoveis").ok is False


async def test_should_keep_listings_when_source_returns_malformed_data(
    session,
    telegram_configured,
    sent_messages,
):
    await monitor.run_check([FakeSource("zap", [found("favorite")])])
    favorite("favorite")

    class MalformedSource:
        name = "zap"

        async def fetch(self, client, criteria):
            raise KeyError("hits")

    result = await monitor.run_check(
        [MalformedSource(), FakeSource("netimoveis", [found("other", source="netimoveis")])],
    )

    active = {listing.external_id: listing.active for listing in all_listings()}
    assert active == {"favorite": True, "other": True}
    assert result.errors == ["ZAP: resposta inválida (KeyError)"]
    assert session.get(SourceStatus, "zap").ok is False
    assert sent_messages == []


async def test_should_alert_cross_posted_apartment_once(session, telegram_configured, sent_messages):
    await monitor.run_check([FakeSource("zap", []), FakeSource("vivareal", [])])
    listing = found("1", rent=1500)
    await monitor.run_check(
        [FakeSource("zap", [listing]), FakeSource("vivareal", [replace(listing, source="vivareal", rent=1520)])],
    )
    assert len(sent_messages) == 1
    assert sent_messages[0].count("Ver no") == 1


async def test_should_retry_alert_after_telegram_failure(session, telegram_configured, monkeypatch):
    await monitor.run_check([FakeSource("zap", [])])

    async def failing_send(*args, **kwargs) -> None:
        raise telegram.TelegramError("Unauthorized")

    monkeypatch.setattr(telegram, "send_message", failing_send)
    failed = await monitor.run_check([FakeSource("zap", [found("1")])])
    assert failed.errors == ["Telegram: Unauthorized"]

    delivered: list[str] = []

    async def working_send(bot_token: str, chat_id: str, html_text: str, link_preview: bool = False) -> None:
        delivered.append(html_text)

    monkeypatch.setattr(telegram, "send_message", working_send)
    await monitor.run_check([FakeSource("zap", [found("1")])])
    assert len(delivered) == 1


def test_should_split_long_alert_into_several_messages():
    alerts = [
        monitor.Alert(
            listing=Listing(**{**found(str(index)).__dict__, "total": 1500, "first_seen": None, "last_seen": None})
        )
        for index in range(40)
    ]
    messages = monitor.format_alert_messages(alerts, [])
    assert len(messages) > 1
    assert all(len(message) <= monitor.MAX_MESSAGE_LENGTH for message in messages)
