from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from app.integrations.unsplash_client import CacheStore, UnsplashClient, UnsplashPhoto

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _fallback_photo(archetype: str, slot: str) -> UnsplashPhoto:
    # Pre-curated default photos live in the R2 bucket under defaults/<archetype>/<slot>.jpg.
    # When Unsplash returns nothing we point the template at those.
    fallback_url = f"https://defaults.sitesnap.app/{archetype}/{slot}.jpg"
    return UnsplashPhoto(
        photo_id=f"fallback-{archetype}-{slot}",
        url_raw=fallback_url,
        url_regular=fallback_url,
        url_small=fallback_url,
        attribution_html="",
        page_url=fallback_url,
    )


def _load_manifest(archetype: str) -> dict:
    path = TEMPLATES_DIR / archetype / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


async def _fetch_one(
    slot: str,
    spec: dict,
    industry: str,
    unsplash: UnsplashClient,
    db: CacheStore,
    archetype: str,
) -> tuple[str, UnsplashPhoto]:
    query = spec["query_template"].format(industry=industry)
    orientation = spec.get("orientation", "landscape")
    try:
        photo = await unsplash.search_cached(query, db=db, orientation=orientation)
    except Exception as e:
        logger.warning("unsplash slot={} query={!r} error={}", slot, query, e)
        photo = None
    if photo is None:
        photo = _fallback_photo(archetype, slot)
    return slot, photo


async def fetch_images_for_archetype(
    *,
    archetype: str,
    industry: str,
    unsplash: UnsplashClient,
    db: CacheStore,
) -> dict[str, UnsplashPhoto]:
    manifest = _load_manifest(archetype)
    slots = manifest["image_slots"]
    results = await asyncio.gather(
        *[_fetch_one(slot, spec, industry, unsplash, db, archetype) for slot, spec in slots.items()]
    )
    return dict(results)
