"""Shared fixtures: isolate every test in its own SQLite database."""

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="apto-pampulha-tests-"))
FRONTEND_DIST_FOR_TESTS = Path(tempfile.mkdtemp(prefix="apto-pampulha-frontend-"))
(FRONTEND_DIST_FOR_TESTS / "index.html").write_text('<div id="app"></div>')
os.environ.setdefault("FRONTEND_DIST", str(FRONTEND_DIST_FOR_TESTS))

import pytest
from sqlmodel import Session, SQLModel

from app.db import engine, init_db

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def session():
    """Fresh database with default settings."""
    SQLModel.metadata.drop_all(engine)
    init_db()
    with Session(engine) as db_session:
        yield db_session


def load_fixture(name: str) -> dict:
    """Load a recorded API response from tests/fixtures."""
    return json.loads((FIXTURES_DIR / name).read_text())
