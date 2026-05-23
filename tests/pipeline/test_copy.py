import json
from unittest.mock import AsyncMock

import pytest

from app.integrations.anthropic_client import ClaudeResponse
from app.pipeline.copy import write_copy

VALID = {
    "headline": "Hand-tied for every season",
    "subheadline": "Bouquets and arrangements from local growers, designed in-shop daily.",
    "primary_cta": "Order now",
    "secondary_cta": "See bouquets",
    "about": {
        "heading": "Locally grown",
        "body": "We source from farms within 50 miles and design every arrangement by hand. Open six mornings a week.",
    },
    "features": [
        {
            "icon": "leaf",
            "title": "From local growers",
            "body": "Every stem is cut within fifty miles of the shop.",
        },
        {
            "icon": "clock",
            "title": "Designed daily",
            "body": "Arrangements are built each morning, never the day before.",
        },
        {
            "icon": "heart",
            "title": "Custom bouquets",
            "body": "Tell us your colors and vibe and we'll design to fit.",
        },
    ],
    "social_proof": [
        {
            "text": "Picked up a bouquet for my mum and she still talks about it.",
            "author": "Sarah K.",
        }
    ],
    "footer_tagline": "Order by noon, delivered same day.",
    "meta": {
        "title": "Bloom Florist",
        "description": "Hand-tied bouquets and arrangements from local growers, designed daily in our Brooklyn shop.",
        "keywords": ["florist", "brooklyn", "bouquet"],
    },
    "palette_hint": "warm-earth",
}


@pytest.fixture
def fake_claude_good():
    c = AsyncMock()
    c.complete_json = AsyncMock(
        return_value=ClaudeResponse(
            text=json.dumps(VALID),
            input_tokens=300,
            output_tokens=400,
            cache_write_tokens=0,
            cache_read_tokens=2200,
            model="claude-sonnet-4-6",
            cost_usd=0.005,
        )
    )
    return c


async def test_write_copy_happy_path(fake_claude_good):
    submission = {
        "full_name": "Jane",
        "email": "j@x.com",
        "brand_name": "Bloom",
        "industry": "florist",
        "questionnaire": {},
    }
    out = await write_copy(claude=fake_claude_good, archetype="service", submission=submission)
    assert out.headline.startswith("Hand-tied")
    assert len(out.features) == 3


async def test_write_copy_retries_then_escalates_to_opus():
    bad = ClaudeResponse(
        text="nope",
        input_tokens=10,
        output_tokens=2,
        cache_write_tokens=0,
        cache_read_tokens=0,
        model="claude-sonnet-4-6",
        cost_usd=0,
    )
    good = ClaudeResponse(
        text=json.dumps(VALID),
        input_tokens=10,
        output_tokens=10,
        cache_write_tokens=0,
        cache_read_tokens=0,
        model="claude-opus-4-7",
        cost_usd=0,
    )
    c = AsyncMock()
    c.complete_json = AsyncMock(side_effect=[bad, bad, good])
    submission = {
        "full_name": "j",
        "email": "j@x.com",
        "brand_name": "B",
        "industry": "i",
        "questionnaire": {},
    }
    out = await write_copy(claude=c, archetype="service", submission=submission)
    assert out.headline.startswith("Hand-tied")
    assert c.complete_json.await_count == 3
    # third call should have used the opus model
    assert c.complete_json.await_args_list[-1].kwargs["model"] == "claude-opus-4-7"
