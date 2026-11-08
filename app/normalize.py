"""Parsing helpers and the filter that decides which listings the user wants."""

import re
import unicodedata

from app.sources.base import FoundListing, SearchCriteria

DIGITS_PATTERN = re.compile(r"\d+")


def matches_criteria(listing: FoundListing, criteria: SearchCriteria) -> bool:
    """Whether a listing is a small, affordable residential rental inside the wanted neighborhoods."""
    if listing.kind is None or listing.rent <= 0:
        return False
    if listing.bedrooms > criteria.max_bedrooms:
        return False
    if criteria.max_area is not None and listing.area is not None and listing.area > criteria.max_area:
        return False
    if criteria.min_total is not None and listing.total < criteria.min_total:
        return False
    if criteria.max_total is not None and listing.total > criteria.max_total:
        return False
    wanted = {normalize_text(name) for name in criteria.neighborhoods}
    return normalize_text(listing.neighborhood) in wanted or normalize_text(listing.alt_neighborhood) in wanted


def canonical_neighborhood(listing: FoundListing, neighborhoods: list[str]) -> str:
    """The configured spelling of the listing's neighborhood, so "São Luíz" and "São Luiz" are one.

    Falls back to the listing's own name when neither of its names is configured.
    """
    by_key = {normalize_text(name): name for name in neighborhoods}
    for candidate in (listing.neighborhood, listing.alt_neighborhood):
        if normalize_text(candidate) in by_key:
            return by_key[normalize_text(candidate)]
    return listing.neighborhood


def normalize_text(value: str) -> str:
    """Lowercase, strip accents and collapse spaces, so "São Luíz" equals "sao luiz"."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.lower().split())


def parse_brl(value: str | None) -> int:
    """Parse "R$ 2.500" (thousands dot, optional cents) into whole reais; blank means zero."""
    if not value:
        return 0
    integer_part = value.split(",")[0]
    digits = "".join(DIGITS_PATTERN.findall(integer_part))
    return int(digits) if digits else 0


def parse_area(value: str | None) -> int | None:
    """Parse "105m²" into 105; None when no number is present."""
    if not value:
        return None
    match = DIGITS_PATTERN.search(value.replace(".", ""))
    return int(match.group()) if match else None


def format_brl(value: int | None) -> str:
    """Format whole reais as "R$ 2.500"."""
    if value is None:
        return "—"
    return f"R$ {value:,}".replace(",", ".")
