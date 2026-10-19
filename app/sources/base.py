"""Common types shared by every listing source."""

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import RENT, SALE
from app.financing import FinancingTerms, estimate


class SourceError(Exception):
    """Raised when a source cannot be fetched or its response cannot be parsed."""


def describe_error(error: Exception) -> str:
    """Short label for a fetch error, with the HTTP status when the server answered one."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}"
    return error.__class__.__name__


@dataclass(frozen=True)
class SearchCriteria:
    """What the user is looking for, as configured in the UI.

    For rentals the price range applies to the monthly total; for sales it
    applies to the sale price, and ``max_monthly`` caps the estimated first
    installment plus condo and IPTU under ``financing``.
    """

    neighborhoods: list[str]
    max_bedrooms: int
    max_area: int | None
    min_total: int | None = None
    max_total: int | None = None
    business: str = RENT
    max_monthly: int | None = None
    financing: FinancingTerms | None = None


@dataclass
class FoundListing:
    """A listing as returned by a source, already in the app's units (whole reais, m²).

    ``rent`` is the monthly rent of a rental and ``sale_price`` the asking price
    of a sale; condo and IPTU are monthly in both cases.
    """

    source: str
    external_id: str
    url: str
    title: str
    kind: str | None
    bedrooms: int
    area: int | None
    rent: int
    condo: int
    iptu: int
    neighborhood: str
    address: str = ""
    image_url: str = ""
    furnished: bool | None = None
    total_override: int | None = None
    alt_neighborhood: str = ""
    business: str = RENT
    sale_price: int | None = None

    @property
    def base_price(self) -> int:
        """The advertised price: the rent of a rental or the sale price of a sale."""
        return (self.sale_price or 0) if self.business == SALE else self.rent

    @property
    def total(self) -> int:
        """Headline price: the sale price of a sale, otherwise the monthly cost of a rental.

        The monthly cost is the source's own total when it has one, otherwise rent + condo + IPTU.
        """
        if self.business == SALE:
            return self.base_price
        if self.total_override is not None:
            return self.total_override
        return self.rent + self.condo + self.iptu

    def monthly_cost(self, terms: FinancingTerms) -> int:
        """Estimated first installment plus condo and IPTU of a sale."""
        return estimate(self.base_price, terms).first_installment + self.condo + self.iptu


class Source(Protocol):
    """A website that can be searched for listings to rent or to buy."""

    name: str

    async def fetch(self, client: httpx.AsyncClient, criteria: SearchCriteria) -> list[FoundListing]:
        """Return every listing of ``criteria.business`` in the searched area; filtering happens afterwards."""
        ...
