from __future__ import annotations

import asyncio
import mimetypes
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.integrations.r2_client import R2Client
from app.settings import settings

HTML_CACHE = "public, max-age=300"
ASSET_CACHE = "public, max-age=31536000, immutable"


def _site_url(slug: str) -> str:
    # Subdomain style: <slug>.<base host>
    parsed = urlparse(settings.r2_public_base)
    host = parsed.netloc or parsed.path  # tolerate URLs without scheme
    scheme = parsed.scheme or "https"
    return f"{scheme}://{slug}.{host}"


async def _download(http: httpx.AsyncClient, url: str) -> bytes:
    resp = await http.get(url, timeout=20.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def _content_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"


async def publish_site(
    *,
    slug: str,
    html: str,
    assets: dict[str, str],  # local_filename -> source URL
    r2: R2Client,
    http: httpx.AsyncClient,
) -> str:
    asset_bytes = await asyncio.gather(*[_download(http, url) for url in assets.values()])
    asset_pairs = dict(zip(assets.keys(), asset_bytes, strict=True))

    items: list[tuple[str, bytes, str, str]] = [
        (f"sites/{slug}/index.html", html.encode("utf-8"), "text/html; charset=utf-8", HTML_CACHE),
    ]
    for local_name, body in asset_pairs.items():
        items.append(
            (
                f"sites/{slug}/{local_name}",
                body,
                _content_type(local_name),
                ASSET_CACHE,
            )
        )

    await r2.put_many(items)
    url = _site_url(slug)
    logger.info("published slug={} url={}", slug, url)
    return url
