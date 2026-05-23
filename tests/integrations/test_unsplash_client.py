from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.integrations.unsplash_client import UnsplashClient, UnsplashPhoto


@respx.mock
async def test_search_returns_first_photo():
    respx.get("https://api.unsplash.com/search/photos").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "abc123",
                        "urls": {
                            "raw": "https://r/x",
                            "regular": "https://r/r",
                            "small": "https://r/s",
                        },
                        "user": {
                            "name": "Jane Photographer",
                            "links": {"html": "https://unsplash.com/@jane"},
                        },
                        "links": {"html": "https://unsplash.com/photos/abc123"},
                    },
                    {"id": "skip"},
                ]
            },
        )
    )
    client = UnsplashClient(http=httpx.AsyncClient())
    photo = await client.search_first("florist arrangement")
    assert isinstance(photo, UnsplashPhoto)
    assert photo.photo_id == "abc123"
    assert "Jane Photographer" in photo.attribution_html


@respx.mock
async def test_search_returns_none_on_empty_results():
    respx.get("https://api.unsplash.com/search/photos").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    client = UnsplashClient(http=httpx.AsyncClient())
    assert await client.search_first("nonsense-query-xyz") is None


@respx.mock
async def test_search_raises_on_5xx():
    respx.get("https://api.unsplash.com/search/photos").mock(return_value=httpx.Response(503))
    client = UnsplashClient(http=httpx.AsyncClient())
    with pytest.raises(httpx.HTTPStatusError):
        await client.search_first("any")


async def test_search_cached_hits_db_first_then_falls_through():
    fake_db = AsyncMock()
    fake_db.fetch_cached_photo = AsyncMock(return_value=None)
    fake_db.store_cached_photo = AsyncMock()

    client = UnsplashClient(http=httpx.AsyncClient())

    async def fake_search(_q, **_kw):
        return UnsplashPhoto(
            photo_id="cached1",
            url_raw="r",
            url_regular="reg",
            url_small="s",
            attribution_html="attr",
            page_url="p",
        )

    client.search_first = fake_search  # type: ignore[assignment]

    photo = await client.search_cached("test-q", db=fake_db, ttl_days=90)
    assert photo and photo.photo_id == "cached1"
    fake_db.store_cached_photo.assert_awaited_once()
