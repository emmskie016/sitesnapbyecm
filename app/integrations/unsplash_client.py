from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

import httpx
from loguru import logger

from app.settings import settings

BASE_URL = "https://api.unsplash.com"


@dataclass
class UnsplashPhoto:
    photo_id: str
    url_raw: str
    url_regular: str
    url_small: str
    attribution_html: str
    page_url: str


class CacheStore(Protocol):
    async def fetch_cached_photo(self, query: str) -> dict | None: ...

    async def store_cached_photo(
        self, *, query: str, photo_id: str, urls: dict, attribution_html: str, page_url: str
    ) -> None: ...


class UnsplashClient:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http or httpx.AsyncClient(timeout=10.0)

    async def search_first(
        self, query: str, *, orientation: str = "landscape"
    ) -> UnsplashPhoto | None:
        resp = await self.http.get(
            f"{BASE_URL}/search/photos",
            params={
                "query": query,
                "per_page": 5,
                "orientation": orientation,
                "content_filter": "high",
            },
            headers={
                "Accept-Version": "v1",
                "Authorization": f"Client-ID {settings.unsplash_access_key}",
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            logger.warning("unsplash empty results for query={}", query)
            return None
        r = results[0]
        user = r.get("user") or {}
        user_name = user.get("name", "Unsplash photographer")
        user_link = (user.get("links") or {}).get("html", "https://unsplash.com")
        page_url = (r.get("links") or {}).get("html", "https://unsplash.com")
        return UnsplashPhoto(
            photo_id=r["id"],
            url_raw=r["urls"]["raw"],
            url_regular=r["urls"]["regular"],
            url_small=r["urls"]["small"],
            attribution_html=(
                f'Photo by <a href="{user_link}?utm_source=sitesnap&utm_medium=referral">'
                f"{user_name}</a> on "
                f'<a href="https://unsplash.com/?utm_source=sitesnap&utm_medium=referral">Unsplash</a>'
            ),
            page_url=page_url,
        )

    async def download(self, url: str) -> bytes:
        resp = await self.http.get(url, timeout=20.0)
        resp.raise_for_status()
        return resp.content

    async def search_cached(
        self,
        query: str,
        *,
        db: CacheStore,
        ttl_days: int = 90,
        orientation: str = "landscape",
    ) -> UnsplashPhoto | None:
        cached = await db.fetch_cached_photo(query)
        if cached and cached["fetched_at"] > datetime.now(UTC) - timedelta(days=ttl_days):
            urls = cached["urls"]
            return UnsplashPhoto(
                photo_id=cached["photo_id"],
                url_raw=urls["raw"],
                url_regular=urls["regular"],
                url_small=urls["small"],
                attribution_html=cached["attribution_html"],
                page_url=cached["page_url"],
            )

        photo = await self.search_first(query, orientation=orientation)
        if photo is not None:
            await db.store_cached_photo(
                query=query,
                photo_id=photo.photo_id,
                urls={"raw": photo.url_raw, "regular": photo.url_regular, "small": photo.url_small},
                attribution_html=photo.attribution_html,
                page_url=photo.page_url,
            )
        return photo


unsplash = UnsplashClient()
