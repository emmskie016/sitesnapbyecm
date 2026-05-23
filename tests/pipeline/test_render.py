from datetime import datetime, timezone

from app.integrations.unsplash_client import UnsplashPhoto
from app.models import CopyOutput
from app.pipeline.render import RenderedSite, render_site

COPY = CopyOutput.model_validate(
    {
        "headline": "Stems and seasons",
        "subheadline": "Hand-tied bouquets from local growers, designed daily.",
        "primary_cta": "Order now",
        "secondary_cta": "See bouquets",
        "about": {
            "heading": "Locally grown",
            "body": "We source from farms within fifty miles and design every arrangement by hand each morning.",
        },
        "features": [
            {
                "icon": "leaf",
                "title": "From local growers",
                "body": "Cut within fifty miles.",
            },
            {
                "icon": "clock",
                "title": "Designed daily",
                "body": "Built every morning.",
            },
            {
                "icon": "heart",
                "title": "Custom bouquets",
                "body": "Tell us colors and vibe.",
            },
        ],
        "social_proof": [{"text": "Stunning.", "author": "Sarah K."}],
        "footer_tagline": "Order by noon, delivered same day.",
        "meta": {
            "title": "Bloom",
            "description": "Hand-tied bouquets.",
            "keywords": ["florist"],
        },
        "palette_hint": "warm-earth",
    }
)

IMAGES = {
    "hero": UnsplashPhoto("p1", "r", "reg", "s", "attr", "pg"),
    "feature_1": UnsplashPhoto("p2", "r", "reg", "s", "attr", "pg"),
    "feature_2": UnsplashPhoto("p3", "r", "reg", "s", "attr", "pg"),
    "feature_3": UnsplashPhoto("p4", "r", "reg", "s", "attr", "pg"),
}


def test_render_service_produces_html_with_palette_and_copy():
    out = render_site(
        archetype="service",
        brand_name="Bloom",
        slug="bloom-x7k2",
        copy=COPY,
        images=IMAGES,
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert isinstance(out, RenderedSite)
    assert "Stems and seasons" in out.html
    assert "#8B5A3C" in out.html  # warm-earth primary
    assert "From local growers" in out.html
    assert out.palette["primary"] == "#8B5A3C"
    assert "bloom-x7k2" in out.html or "Bloom" in out.html


def test_render_hospitality_works():
    out = render_site(
        archetype="hospitality",
        brand_name="Loaf",
        slug="loaf-abcd",
        copy=COPY,
        images=IMAGES,
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert "Stems and seasons" in out.html
