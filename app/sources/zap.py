"""ZAP Imóveis and VivaReal, which share Grupo OLX's "glue" listings API.

The portal is selected by the ``x-domain`` header. The API filters bedrooms
reliably but ignores property-type filters, so non-residential units are
dropped while parsing.
"""

import asyncio
import logging

import httpx

from app.config import RENT, SALE, SECONDS_BETWEEN_REQUESTS, USER_AGENT
from app.sources.base import FoundListing, SearchCriteria, SourceError, describe_error

logger = logging.getLogger(__name__)

API_URL = "https://glue-api.zapimoveis.com.br/v2/listings"
PAGE_SIZE = 30
MAX_PAGES_PER_NEIGHBORHOOD = 10
IMAGE_SIZE = "360x240"
BUSINESS_TYPES = {RENT: "RENTAL", SALE: "SALE"}

PORTALS: dict[str, tuple[str, str]] = {
    "zap": (".zapimoveis.com.br", "https://www.zapimoveis.com.br"),
    "vivareal": (".vivareal.com.br", "https://www.vivareal.com.br"),
}
KINDS: dict[str, str] = {
    "APARTMENT": "apartment",
    "STUDIO": "studio",
    "KITNET": "studio",
    "FLAT": "flat",
    "LOFT": "loft",
    "PENTHOUSE": "penthouse",
}


class GlueSource:
    """Searches rentals or sales on ZAP or VivaReal, one neighborhood at a time."""

    def __init__(self, name: str) -> None:
        """Bind the source to one portal ("zap" or "vivareal")."""
        self.name = name
        self.domain, self.site_url = PORTALS[name]

    async def fetch(self, client: httpx.AsyncClient, criteria: SearchCriteria) -> list[FoundListing]:
        """Fetch listings with 1 to ``criteria.max_bedrooms`` bedrooms in every configured neighborhood."""
        listings: list[FoundListing] = []
        for index, neighborhood in enumerate(criteria.neighborhoods):
            if index:
                await asyncio.sleep(SECONDS_BETWEEN_REQUESTS)
            listings.extend(await self._fetch_neighborhood(client, neighborhood, criteria))
        return listings

    async def _fetch_neighborhood(
        self,
        client: httpx.AsyncClient,
        neighborhood: str,
        criteria: SearchCriteria,
    ) -> list[FoundListing]:
        """Page through one neighborhood's results."""
        listings: list[FoundListing] = []
        for page in range(MAX_PAGES_PER_NEIGHBORHOOD):
            if page:
                await asyncio.sleep(SECONDS_BETWEEN_REQUESTS)
            search = await self._get_page(client, neighborhood, criteria, page * PAGE_SIZE)
            items = search["result"]["listings"]
            listings.extend(
                listing
                for item in items
                if (listing := parse_item(item, self.name, self.site_url, criteria.business)) is not None
            )
            if (page + 1) * PAGE_SIZE >= search.get("totalCount", 0) or not items:
                break
        return listings

    async def _get_page(
        self,
        client: httpx.AsyncClient,
        neighborhood: str,
        criteria: SearchCriteria,
        offset: int,
    ) -> dict:
        """GET one page of results and return its ``search`` object."""
        params = {
            "business": BUSINESS_TYPES[criteria.business],
            "categoryPage": "RESULT",
            "addressCity": "Belo Horizonte",
            "addressState": "Minas Gerais",
            "addressNeighborhood": neighborhood,
            "bedrooms": ",".join(str(count) for count in range(1, max(criteria.max_bedrooms, 1) + 1)),
            "size": PAGE_SIZE,
            "from": offset,
        }
        try:
            response = await client.get(
                API_URL,
                params=params,
                headers={"User-Agent": USER_AGENT, "x-domain": self.domain, "Origin": self.site_url},
            )
            response.raise_for_status()
            return response.json()["search"]
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise SourceError(f"{self.name}: {describe_error(error)} em {neighborhood}") from error


def parse_item(item: dict, source: str, site_url: str, business: str = RENT) -> FoundListing | None:
    """Convert one API result into a FoundListing, or None if it is not residential or lacks that price.

    A unit offered both to rent and to buy carries one pricing entry per business.
    """
    data = item["listing"]
    if "RESIDENTIAL" not in data.get("usageTypes", []):
        return None
    business_type = BUSINESS_TYPES[business]
    pricing = next((info for info in data.get("pricingInfos", []) if info.get("businessType") == business_type), None)
    if pricing is None:
        return None
    address = data.get("address") or {}
    link = item.get("link") or {}
    price = int(pricing.get("price") or 0)
    return FoundListing(
        source=source,
        external_id=str(data["id"]),
        url=f"{site_url}{link.get('href', '')}",
        title=link.get("name") or data.get("title") or "Imóvel",
        kind=_kind(data),
        bedrooms=_first(data.get("bedrooms")) or 0,
        area=_first(data.get("usableAreas")),
        rent=0 if business == SALE else price,
        condo=int(pricing.get("monthlyCondoFee") or 0),
        iptu=round(int(pricing.get("yearlyIptu") or 0) / 12),
        neighborhood=address.get("neighborhood") or "",
        alt_neighborhood=(link.get("data") or {}).get("neighborhood") or "",
        address=" ".join(part for part in (address.get("street"), address.get("streetNumber")) if part),
        image_url=_image_url(item.get("medias") or []),
        business=business,
        sale_price=price if business == SALE else None,
    )


def _kind(data: dict) -> str | None:
    """Map unit (sub)types to the app's kinds; a subtype like KITNET wins over APARTMENT."""
    for unit_type in [*data.get("unitSubTypes", []), *data.get("unitTypes", [])]:
        if unit_type in KINDS:
            return KINDS[unit_type]
    return None


def _first(values: list | None) -> int | None:
    """First element of the API's single-value lists."""
    return int(values[0]) if values else None


def _image_url(medias: list[dict]) -> str:
    """Fill the resize template of the first image."""
    image = next((media for media in medias if media.get("type") == "IMAGE"), None)
    if image is None:
        return ""
    width, height = IMAGE_SIZE.split("x")
    return (
        image["url"]
        .replace("{description}", "imovel")
        .replace("{action}", "fit-in")
        .replace("{width}", width)
        .replace("{height}", height)
    )
