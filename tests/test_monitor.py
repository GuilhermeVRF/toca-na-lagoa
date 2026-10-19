"""Tests for the check routine: storing listings, price history and alerts."""

from dataclasses import replace

import pytest
from sqlmodel import Session, select

from app import monitor, telegram
from app.config import RENT, SALE
from app.db import engine, load_settings
from app.models import Listing, PriceHistory, SourceStatus
from app.sources.base import FoundListing, SearchCriteria, SourceError


class FakeSource:
    """Source returning the fixed listings of the requested business, or raising when ``error`` is set."""

    def __init__(self, name: str, listings: list[FoundListing], error: str = "") -> None:
        self.name = name
        self.listings = listings
        self.error = error
        self.searched: list[str] = []

    async def fetch(self, client, criteria: SearchCriteria) -> list[FoundListing]:
        self.searched.append(criteria.business)
        if self.error:
            raise SourceError(self.error)
        return [listing for listing in self.listings if listing.business == criteria.business]


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
    assert session.get(SourceStatus, ("netimoveis", "rent")).ok is False


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
    assert session.get(SourceStatus, ("zap", "rent")).ok is False
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


def for_sale(external_id: str, price: int = 300_000, source: str = "zap", **overrides) -> FoundListing:
    """A listing for sale that matches the default sale settings."""
    return found(external_id, source=source, rent=0, business=SALE, sale_price=price, condo=300, **overrides)


@pytest.fixture
def sales_enabled(session):
    """Turn the sale search on with the default financing terms."""
    settings = load_settings(session)
    settings.sale_enabled = True
    session.add(settings)
    session.commit()


async def test_should_search_only_rentals_while_sales_are_off(session):
    source = FakeSource("zap", [found("1"), for_sale("2")])
    await monitor.run_check([source])
    assert source.searched == [RENT]
    assert [listing.business for listing in all_listings()] == [RENT]


async def test_should_store_the_same_unit_once_per_business(session, sales_enabled):
    await monitor.run_check([FakeSource("zap", [found("1"), for_sale("1")])])
    stored = all_listings()
    assert sorted((listing.business, listing.total) for listing in stored) == [(RENT, 1500), (SALE, 300_000)]
    assert {listing.group_id for listing in stored} == {None}
    assert session.get(SourceStatus, ("zap", SALE)).found == 1


async def test_should_fill_sales_silently_once_even_after_rentals_were_filled(
    session,
    telegram_configured,
    sent_messages,
):
    await monitor.run_check([FakeSource("zap", [found("1")])])
    settings = load_settings(session)
    settings.sale_enabled = True
    session.add(settings)
    session.commit()

    await monitor.run_check([FakeSource("zap", [found("1"), for_sale("10")])])
    assert sent_messages == []

    await monitor.run_check([FakeSource("zap", [found("1"), for_sale("10"), for_sale("11", price=320_000)])])
    assert len(sent_messages) == 1
    assert "1 apartamento(s) novo(s) à venda" in sent_messages[0]
    assert "R$ 320.000" in sent_messages[0]
    assert "/mês (SAC, entrada R$ 64.000)" in sent_messages[0]


async def test_should_say_a_retired_favorite_for_sale_was_probably_sold(
    session,
    telegram_configured,
    sales_enabled,
    sent_messages,
):
    await monitor.run_check([FakeSource("zap", [for_sale("1")])])
    with Session(engine) as db_session:
        listing = db_session.exec(select(Listing)).one()
        listing.favorite = True
        listing.start_watching()
        db_session.add(listing)
        db_session.commit()

    await monitor.run_check([FakeSource("zap", [])])
    assert "provavelmente foi vendido" in sent_messages[0]


async def test_should_apply_sale_criteria_to_sales(session, sales_enabled):
    settings = load_settings(session)
    settings.sale_max_price = 350_000
    session.add(settings)
    session.commit()
    await monitor.run_check([FakeSource("zap", [for_sale("cheap", 300_000), for_sale("pricey", 400_000)])])
    assert [listing.external_id for listing in all_listings()] == ["cheap"]
