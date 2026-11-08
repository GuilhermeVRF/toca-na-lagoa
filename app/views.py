"""View models assembled for the listings page."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlmodel import Session, col, select

from app.config import TIMEZONE
from app.models import Listing, PriceHistory

NEW_LISTING_HOURS = 24

SORT_KEYS = {
    "total": lambda card: card.listing.total,
    "rent": lambda card: card.listing.rent,
    "area": lambda card: card.listing.area or 0,
    "price_m2": lambda card: card.price_per_m2 if card.price_per_m2 is not None else float("inf"),
    "recent": lambda card: card.listing.first_seen,
}
SORT_LABELS = {
    "total": "Preço total",
    "rent": "Aluguel",
    "area": "Área",
    "price_m2": "R$/m²",
    "recent": "Mais recentes",
}


@dataclass
class ListingFilters:
    """Filters and ordering chosen on the listings page."""

    sort: str = "total"
    order: str = "asc"
    neighborhood: str = ""
    kind: str = ""
    source: str = ""
    furnished: bool = False
    only_new: bool = False
    favorites: bool = False
    show_hidden: bool = False
    show_inactive: bool = False

    @classmethod
    def from_query(cls, params: dict[str, str]) -> "ListingFilters":
        """Read filters from query parameters, falling back to defaults on bad values."""
        sort = params.get("sort", "total")
        order = params.get("order", "desc" if sort == "recent" else "asc")
        return cls(
            sort=sort if sort in SORT_KEYS else "total",
            order=order if order in ("asc", "desc") else "asc",
            neighborhood=params.get("neighborhood", ""),
            kind=params.get("kind", ""),
            source=params.get("source", ""),
            furnished=params.get("furnished") == "1",
            only_new=params.get("only_new") == "1",
            favorites=params.get("favorites") == "1",
            show_hidden=params.get("show_hidden") == "1",
            show_inactive=params.get("show_inactive") == "1",
        )


@dataclass
class ListingCard:
    """One apartment on the page, with its copies on other portals."""

    listing: Listing
    copies: list[Listing] = field(default_factory=list)
    history: list[PriceHistory] = field(default_factory=list)
    is_new: bool = False

    @property
    def price_per_m2(self) -> float | None:
        """Total monthly cost per square meter."""
        if not self.listing.area:
            return None
        return self.listing.total / self.listing.area

    @property
    def previous_total(self) -> int | None:
        """The price before the latest change, if the price ever changed."""
        return self.history[-2].total if len(self.history) >= 2 else None


def build_listing_cards(session: Session, filters: ListingFilters) -> list[ListingCard]:
    """Load, filter, collapse duplicates and sort the listings for display."""
    listings = session.exec(_listing_query(filters)).all()
    new_since = (datetime.now(TIMEZONE) - timedelta(hours=NEW_LISTING_HOURS)).replace(tzinfo=None)
    cards = _collapse_groups(listings)
    if filters.only_new:
        cards = [card for card in cards if card.listing.first_seen >= new_since]
    _attach_history(session, cards)
    for card in cards:
        card.is_new = card.listing.first_seen >= new_since
    cards.sort(key=SORT_KEYS[filters.sort], reverse=filters.order == "desc")
    return cards


def _listing_query(filters: ListingFilters):
    """SQL query for the listings matching the column filters."""
    query = select(Listing)
    if not (filters.show_inactive or filters.favorites):
        query = query.where(Listing.active)
    if not filters.show_hidden:
        query = query.where(col(Listing.hidden).is_(False))
    if filters.favorites:
        query = query.where(Listing.favorite)
    if filters.neighborhood:
        query = query.where(Listing.neighborhood == filters.neighborhood)
    if filters.kind:
        query = query.where(Listing.kind == filters.kind)
    if filters.source:
        query = query.where(Listing.source == filters.source)
    if filters.furnished:
        query = query.where(Listing.furnished)
    return query


def _collapse_groups(listings: list[Listing]) -> list[ListingCard]:
    """One card per apartment: the cheapest copy leads, the others become links."""
    cards: list[ListingCard] = []
    by_group: dict[int, list[Listing]] = {}
    for listing in listings:
        if listing.group_id is None:
            cards.append(ListingCard(listing=listing))
        else:
            by_group.setdefault(listing.group_id, []).append(listing)
    for members in by_group.values():
        cheapest, *others = sorted(members, key=lambda listing: listing.total)
        cards.append(ListingCard(listing=cheapest, copies=others))
    return cards


def _attach_history(session: Session, cards: list[ListingCard]) -> None:
    """Load the price history of each card's leading listing."""
    by_id = {card.listing.id: card for card in cards}
    if not by_id:
        return
    rows = session.exec(
        select(PriceHistory)
        .where(col(PriceHistory.listing_id).in_(list(by_id)))
        .order_by(col(PriceHistory.observed_at)),
    ).all()
    for row in rows:
        by_id[row.listing_id].history.append(row)


def neighborhood_options(session: Session) -> list[str]:
    """Neighborhoods that currently have active listings, for the filter dropdown."""
    return sorted(set(session.exec(select(Listing.neighborhood).where(Listing.active)).all()))
