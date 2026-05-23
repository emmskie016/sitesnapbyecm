from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from app.integrations.unsplash_client import CacheStore, UnsplashClient, UnsplashPhoto

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _fallback_photo(archetype: str, slot: str) -> UnsplashPhoto:
    # Public no-key placeholder service so the pipeline always succeeds.
    # Seed is deterministic per archetype+slot for consistent imagery.
    seed = f"{archetype}-{slot}"
    return UnsplashPhoto(
        photo_id=f"fallback-{seed}",
        url_raw=f"https://picsum.photos/seed/{seed}/1600/900",
        url_regular=f"https://picsum.photos/seed/{seed}/1600/900",
        url_small=f"https://picsum.photos/seed/{seed}/400/300",
        attribution_html='Photo via <a href="https://picsum.photos">picsum.photos</a>',
        page_url=f"https://picsum.photos/seed/{seed}",
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
