"""Common types shared by every listing source."""

from dataclasses import dataclass
from typing import Protocol

import httpx


class SourceError(Exception):
    """Raised when a source cannot be fetched or its response cannot be parsed."""


def describe_error(error: Exception) -> str:
    """Short label for a fetch error, with the HTTP status when the server answered one."""
    if isinstance(error, httpx.HTTPStatusError):
        return f"HTTP {error.response.status_code}"
    return error.__class__.__name__


@dataclass(frozen=True)
class SearchCriteria:
    """What the user is looking for, as configured in the UI."""

    neighborhoods: list[str]
    max_bedrooms: int
    max_area: int | None
    min_total: int | None = None
    max_total: int | None = None


@dataclass
class FoundListing:
    """A listing as returned by a source, already in the app's units (whole reais, m²)."""

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

    @property
    def total(self) -> int:
        """Monthly cost: the source's own total when it has one, otherwise rent + condo + IPTU."""
        if self.total_override is not None:
            return self.total_override
        return self.rent + self.condo + self.iptu


class Source(Protocol):
    """A website that can be searched for rental listings."""

    name: str

    async def fetch(self, client: httpx.AsyncClient, criteria: SearchCriteria) -> list[FoundListing]:
        """Return every listing in the searched area; filtering by criteria happens afterwards."""
        ...
