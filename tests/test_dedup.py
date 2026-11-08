"""Tests for cross-portal duplicate grouping."""

from app.dedup import GroupCandidate, assign_groups


def candidate(listing_id: int, source: str, area: int | None = 40, price: int = 1500, neighborhood: str = "Castelo"):
    """Build a candidate with sensible defaults."""
    return GroupCandidate(listing_id=listing_id, source=source, neighborhood=neighborhood, area=area, price=price)


def test_should_group_same_apartment_on_different_portals():
    groups = assign_groups([candidate(1, "zap"), candidate(2, "netimoveis", area=42, price=1550)])
    assert groups == {1: 1, 2: 1}


def test_should_not_group_listings_from_the_same_portal():
    assert assign_groups([candidate(1, "zap"), candidate(2, "zap")]) == {1: None, 2: None}


def test_should_not_group_when_price_differs_too_much():
    assert assign_groups([candidate(1, "zap"), candidate(2, "vivareal", price=1800)]) == {1: None, 2: None}


def test_should_not_group_when_area_is_unknown():
    assert assign_groups([candidate(1, "zap", area=None), candidate(2, "vivareal")]) == {1: None, 2: None}


def test_should_group_transitively_under_smallest_id():
    groups = assign_groups([candidate(5, "zap"), candidate(3, "vivareal"), candidate(9, "netimoveis")])
    assert groups == {5: 3, 3: 3, 9: 3}


def test_should_not_chain_similar_units_into_one_group():
    chain = [
        candidate(1, "zap", price=300_000),
        candidate(2, "vivareal", price=310_000),
        candidate(3, "zap", price=320_000),
        candidate(4, "vivareal", price=330_000),
    ]
    groups = assign_groups(chain)
    assert sorted(groups.values()) == [1, 1, 3, 3]


def test_should_pair_the_closest_copy_first():
    groups = assign_groups(
        [candidate(1, "zap", price=1500), candidate(2, "vivareal", price=1560), candidate(3, "vivareal", price=1500)]
    )
    assert groups == {1: 1, 2: None, 3: 1}
