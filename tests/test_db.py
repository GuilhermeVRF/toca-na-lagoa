"""Tests for upgrading a database created by an older version of the app."""

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, select

from app.db import engine, init_db
from app.models import Listing, PriceHistory, Settings, SourceStatus

# An older schema: extra columns, and keys that also included a ``business`` column.
LEGACY_SCHEMA = [
    """CREATE TABLE settings (
        id INTEGER NOT NULL PRIMARY KEY, enabled BOOLEAN NOT NULL, check_times VARCHAR NOT NULL,
        neighborhoods VARCHAR NOT NULL, max_bedrooms INTEGER NOT NULL, max_area INTEGER, min_total INTEGER,
        max_total INTEGER, initial_sync_done BOOLEAN NOT NULL, sale_enabled BOOLEAN NOT NULL,
        sale_max_bedrooms INTEGER NOT NULL, sale_max_area INTEGER, sale_min_price INTEGER, sale_max_price INTEGER,
        sale_max_monthly INTEGER, sale_initial_sync_done BOOLEAN NOT NULL,
        financing_down_payment_percent INTEGER NOT NULL, financing_rate FLOAT NOT NULL,
        financing_term_years INTEGER NOT NULL, financing_system VARCHAR NOT NULL,
        telegram_bot_token VARCHAR NOT NULL, telegram_chat_id VARCHAR NOT NULL, last_check_at DATETIME,
        last_check_status VARCHAR NOT NULL)""",
    """CREATE TABLE listing (
        id INTEGER NOT NULL PRIMARY KEY, source VARCHAR NOT NULL, business VARCHAR NOT NULL,
        external_id VARCHAR NOT NULL, url VARCHAR NOT NULL, title VARCHAR NOT NULL, kind VARCHAR NOT NULL,
        bedrooms INTEGER NOT NULL, area INTEGER, rent INTEGER NOT NULL, sale_price INTEGER,
        condo INTEGER NOT NULL, iptu INTEGER NOT NULL, total INTEGER NOT NULL, neighborhood VARCHAR NOT NULL,
        address VARCHAR NOT NULL, image_url VARCHAR NOT NULL, furnished BOOLEAN, first_seen DATETIME NOT NULL,
        last_seen DATETIME NOT NULL, active BOOLEAN NOT NULL, favorite BOOLEAN NOT NULL, hidden BOOLEAN NOT NULL,
        group_id INTEGER, notified BOOLEAN NOT NULL, watched_total INTEGER, watched_active BOOLEAN,
        UNIQUE (source, business, external_id))""",
    "CREATE INDEX ix_listing_business ON listing (business)",
    """CREATE TABLE sourcestatus (
        source VARCHAR NOT NULL, business VARCHAR NOT NULL, last_run_at DATETIME, ok BOOLEAN NOT NULL,
        found INTEGER NOT NULL, error VARCHAR NOT NULL, PRIMARY KEY (source, business))""",
    """CREATE TABLE pricehistory (
        id INTEGER NOT NULL PRIMARY KEY, listing_id INTEGER NOT NULL REFERENCES listing (id),
        observed_at DATETIME NOT NULL, total INTEGER NOT NULL)""",
    """INSERT INTO settings VALUES (1, 1, '08:00', 'São Luiz', 1, 70, NULL, 2500, 1, 1, 2, NULL, NULL, 400000,
        NULL, 1, 20, 11.5, 30, 'sac', 'token', 'chat', NULL, 'ok')""",
    """INSERT INTO listing VALUES (7, 'zap', 'rent', '42', 'https://example.com/42', 'Apto', 'apartment', 1, 40,
        1500, NULL, 0, 0, 1500, 'São Luiz', '', '', NULL, '2026-10-01 08:00:00', '2026-10-01 08:00:00', 1, 1, 0,
        NULL, 1, 1500, 1)""",
    "INSERT INTO pricehistory VALUES (1, 7, '2026-10-01 08:00:00', 1500)",
    "INSERT INTO sourcestatus VALUES ('zap', 'rent', '2026-10-01 08:00:00', 1, 1, '')",
]


def test_should_rebuild_changed_keys_and_drop_removed_columns(session):
    session.close()
    SQLModel.metadata.drop_all(engine)
    with engine.begin() as connection:
        for statement in LEGACY_SCHEMA:
            connection.execute(text(statement))

    init_db()

    with Session(engine) as db_session:
        assert [listing.id for listing in db_session.exec(select(Listing)).all()] == [7]
        assert db_session.get(Listing, 7).favorite
        assert [entry.listing_id for entry in db_session.exec(select(PriceHistory)).all()] == [7]
        assert [status.source for status in db_session.exec(select(SourceStatus)).all()] == ["zap"]
        settings = db_session.get(Settings, 1)
        assert (settings.max_total, settings.telegram_chat_id) == (2500, "chat")
    inspector = inspect(engine)
    unique_keys = [unique["column_names"] for unique in inspector.get_unique_constraints("listing")]
    assert sorted(map(sorted, unique_keys)) == [["external_id", "source"]]
    for table_name in ("listing", "sourcestatus", "settings"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert not {name for name in columns if "sale" in name or "financing" in name or name == "business"}


def test_should_not_rebuild_an_up_to_date_database(session, monkeypatch):
    rebuilt: list[str] = []
    monkeypatch.setattr("app.db._rebuild_table", lambda connection, table: rebuilt.append(table.name))
    init_db()
    assert rebuilt == []
