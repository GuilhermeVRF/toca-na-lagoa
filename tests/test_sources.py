"""Tests for parsing recorded responses of each source."""

import httpx
import pytest
import respx

from app.sources import netimoveis, quintoandar, zap
from app.sources.base import SearchCriteria, SourceError
from tests.conftest import load_fixture

CRITERIA = SearchCriteria(neighborhoods=["São Luiz"], max_bedrooms=1, max_area=None)


def test_should_parse_quintoandar_hit():
    hits = load_fixture("quintoandar_search.json")["hits"]["hits"]
    listing = quintoandar.parse_hit(hits[0]["_source"])
    assert listing.external_id == "894801089"
    assert listing.url == "https://www.quintoandar.com.br/imovel/894801089"
    assert listing.kind == "apartment"
    assert (listing.rent, listing.total) == (4500, 6031)
    assert (listing.neighborhood, listing.alt_neighborhood) == ("São Luíz", "Pampulha")
    assert listing.image_url.startswith("https://www.quintoandar.com.br/img/med/")


def test_should_mark_quintoandar_houses_as_unwanted_kind():
    hits = load_fixture("quintoandar_search.json")["hits"]["hits"]
    kinds = {hit["_source"]["type"]: quintoandar.parse_hit(hit["_source"]).kind for hit in hits}
    assert kinds == {"Apartamento": "apartment", "StudioOuKitchenette": "studio", "Casa": None}


def test_should_parse_zap_residential_listing():
    items = load_fixture("zap_listings.json")["search"]["result"]["listings"]
    listing = zap.parse_item(items[0], "zap", "https://www.zapimoveis.com.br")
    assert listing.external_id == "2911269940"
    assert listing.kind == "penthouse"
    assert (listing.rent, listing.condo, listing.iptu) == (6500, 600, 0)
    assert listing.url.startswith("https://www.zapimoveis.com.br/imovel/")
    assert "{" not in listing.image_url


def test_should_skip_zap_commercial_listing():
    items = load_fixture("zap_listings.json")["search"]["result"]["listings"]
    commercial = [item for item in items if "COMMERCIAL" in item["listing"]["usageTypes"]]
    assert zap.parse_item(commercial[0], "zap", "https://www.zapimoveis.com.br") is None


def test_should_parse_netimoveis_item():
    items = load_fixture("netimoveis_search.json")["imovelCampos"]
    listing = netimoveis.parse_item(items[0])
    assert listing.external_id == "1080699"
    assert listing.kind == "penthouse"
    assert (listing.rent, listing.condo, listing.iptu, listing.area) == (3500, 250, 109, 121)
    assert listing.neighborhood == "Castelo"
    assert listing.url.startswith("https://www.netimoveis.com/imovel/")


@respx.mock
async def test_should_page_through_zap_until_total_count(monkeypatch):
    first_page = load_fixture("zap_listings.json")
    first_page["search"]["totalCount"] = 35
    second_page = {"search": {"totalCount": 35, "result": {"listings": []}}}
    route = respx.get(zap.API_URL).mock(
        side_effect=[httpx.Response(200, json=first_page), httpx.Response(200, json=second_page)],
    )
    monkeypatch.setattr(zap, "SECONDS_BETWEEN_REQUESTS", 0)
    async with httpx.AsyncClient() as client:
        listings = await zap.GlueSource("vivareal").fetch(client, CRITERIA)
    assert route.call_count == 2
    assert route.calls[0].request.headers["x-domain"] == ".vivareal.com.br"
    assert {listing.source for listing in listings} == {"vivareal"}


@respx.mock
async def test_should_raise_source_error_on_http_failure():
    respx.post(quintoandar.SEARCH_URL).mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        with pytest.raises(SourceError):
            await quintoandar.QuintoAndarSource().fetch(client, CRITERIA)


@respx.mock
async def test_should_stop_netimoveis_paging_at_total():
    body = load_fixture("netimoveis_search.json")
    route = respx.post(netimoveis.SEARCH_URL).mock(return_value=httpx.Response(200, json=body))
    async with httpx.AsyncClient() as client:
        listings = await netimoveis.NetimoveisSource().fetch(client, CRITERIA)
    assert route.call_count == 1
    assert len(listings) == len(body["imovelCampos"])
