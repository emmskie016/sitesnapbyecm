import json
from unittest.mock import AsyncMock

import pytest

from app.integrations.unsplash_client import UnsplashPhoto
from app.pipeline.images import fetch_images_for_archetype


@pytest.fixture
def fake_manifest(tmp_path, monkeypatch):
    archetype_dir = tmp_path / "service"
    archetype_dir.mkdir(parents=True)
    (archetype_dir / "manifest.json").write_text(
        json.dumps(
            {
                "archetype": "service",
                "image_slots": {
                    "hero": {
                        "query_template": "{industry} pro",
                        "orientation": "landscape",
                    },
                    "feature_1": {
                        "query_template": "{industry} office",
                        "orientation": "squarish",
                    },
                    "feature_2": {
                        "query_template": "{industry} happy",
                        "orientation": "squarish",
                    },
                    "feature_3": {
                        "query_template": "{industry} together",
                        "orientation": "squarish",
                    },
                },
            }
        )
    )
    monkeypatch.setattr("app.pipeline.images.TEMPLATES_DIR", tmp_path)
    return tmp_path


async def test_fetch_images_uses_cache_then_unsplash(fake_manifest):
    unsplash = AsyncMock()
    unsplash.search_cached = AsyncMock(
        return_value=UnsplashPhoto(
            photo_id="p1",
            url_raw="r",
            url_regular="reg",
            url_small="s",
            attribution_html="attr",
            page_url="pg",
        )
    )
    fake_db = AsyncMock()

    images = await fetch_images_for_archetype(
        archetype="service",
        industry="dentist",
        unsplash=unsplash,
        db=fake_db,
    )
    assert set(images.keys()) == {"hero", "feature_1", "feature_2", "feature_3"}
    assert all(p.photo_id == "p1" for p in images.values())
    assert unsplash.search_cached.await_count == 4


async def test_fetch_images_falls_back_when_unsplash_returns_none(fake_manifest):
    unsplash = AsyncMock()
    unsplash.search_cached = AsyncMock(return_value=None)
    fake_db = AsyncMock()

    images = await fetch_images_for_archetype(
        archetype="service",
        industry="x",
        unsplash=unsplash,
        db=fake_db,
    )
    assert all(p is not None for p in images.values())
    # fallback photos use the placeholder photo_id sentinel
    assert all(p.photo_id.startswith("fallback-") for p in images.values())
