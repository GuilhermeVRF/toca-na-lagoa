"""Netimóveis, the portal shared by Belo Horizonte's real-estate agencies.

Uses the JSON endpoint behind its listing page. The endpoint ignores bedroom
filters, so the whole Pampulha region is paged through and filtered afterwards.
"""

import asyncio
import logging
from urllib.parse import parse_qs, urlsplit

import httpx

from app.config import SECONDS_BETWEEN_REQUESTS
from app.normalize import parse_area, parse_brl
from app.sources.base import FoundListing, SearchCriteria, SourceError, describe_error

logger = logging.getLogger(__name__)

SITE_URL = "https://www.netimoveis.com"
SEARCH_URL = f"{SITE_URL}/Listagem/Buscar"
IMAGE_URL = "https://img.netimoveis.com/fotos-imoveis/{path}"
PAGE_SIZE = 21
MAX_PAGES = 20

KINDS: dict[str, str] = {
    "apartamento": "apartment",
    "area-privativa": "apartment",
    "cobertura": "penthouse",
    "kitnet": "studio",
    "studio": "studio",
    "flat": "flat",
    "loft": "loft",
}


class NetimoveisSource:
    """Searches rentals on Netimóveis."""

    name = "netimoveis"

    async def fetch(self, client: httpx.AsyncClient, criteria: SearchCriteria) -> list[FoundListing]:
        """Fetch every apartment-like rental in the Pampulha region."""
        listings: list[FoundListing] = []
        for page in range(1, MAX_PAGES + 1):
            if page > 1:
                await asyncio.sleep(SECONDS_BETWEEN_REQUESTS)
            body = await _post_search(client, page)
            items = body.get("imovelCampos") or []
            listings.extend(parse_item(item) for item in items)
            if not items or page * PAGE_SIZE >= int(body.get("quantidadeTotalImoveis") or 0):
                break
        return listings


async def _post_search(client: httpx.AsyncClient, page: int) -> dict:
    """POST one page of the region search and return the decoded body."""
    payload = {
        "formato": "lista",
        "coordenadas": [],
        "registrosPorPagina": PAGE_SIZE,
        "pagina": page,
        "transacao": "locacao",
        "tipos": list(KINDS),
        "localizacao": {
            "urlEstado": "minas-gerais",
            "urlCidade": "belo-horizonte",
            "urlRegiao": "pampulha",
            "urlBairro": "",
            "urlLogradouro": "",
            "urlTipoLocalizacao": "Regiao",
        },
        "order": "mais-recente",
        "modoBusca": "csr",
    }
    try:
        response = await client.post(
            SEARCH_URL,
            json=payload,
            headers={
                "Origin": SITE_URL,
                "Referer": f"{SITE_URL}/locacao/minas-gerais/belo-horizonte/pampulha/apartamento",
                "X-Listagem-Fetch-Source": "csr",
            },
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise SourceError(f"Netimóveis: {describe_error(error)}") from error
    if body.get("erro"):
        raise SourceError(f"Netimóveis: {body.get('mensagem') or 'erro na busca'}")
    return body


def parse_item(item: dict) -> FoundListing:
    """Convert one search result into a FoundListing."""
    link = item.get("link") or ""
    photos = item.get("fotos") or []
    return FoundListing(
        source="netimoveis",
        external_id=str(item["imovel_id"]),
        url=f"{SITE_URL}{link}",
        title=item.get("titulo") or "Imóvel para alugar",
        kind=KINDS.get(_listing_type(link)),
        bedrooms=int(item.get("quartos") or 0),
        area=parse_area(item.get("areaRealPrivativa")),
        rent=parse_brl(item.get("valorImovel")),
        condo=parse_brl(item.get("valorCondominio")),
        iptu=parse_brl(item.get("valorIptu")),
        neighborhood=item.get("bairro") or "",
        address=item.get("logradouro") or "",
        image_url=IMAGE_URL.format(path=photos[0]["foto"]) if photos else "",
    )


def _listing_type(link: str) -> str:
    """Read the property type from the ``tipoUrl`` query parameter of a listing link."""
    values = parse_qs(urlsplit(link).query).get("tipoUrl") or [""]
    return values[0]
