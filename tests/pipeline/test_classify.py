from unittest.mock import AsyncMock

import pytest

from app.integrations.anthropic_client import ClaudeResponse
from app.pipeline.classify import classify_submission


@pytest.fixture
def fake_claude():
    client = AsyncMock()
    client.complete_json = AsyncMock(
        return_value=ClaudeResponse(
            text='{"archetype":"hospitality","confidence":0.92,"reasoning":"r"}',
            input_tokens=100,
            output_tokens=20,
            cache_write_tokens=0,
            cache_read_tokens=1200,
            model="claude-sonnet-4-6",
            cost_usd=0.001,
        )
    )
    return client


async def test_classify_returns_parsed_output(fake_claude):
    out = await classify_submission(
        claude=fake_claude,
        industry="bakery",
        brand_name="Loaf",
        questionnaire={"tone": "warm"},
    )
    assert out.archetype == "hospitality"
    assert out.confidence == pytest.approx(0.92)


async def test_classify_falls_back_when_low_confidence():
    client = AsyncMock()
    client.complete_json = AsyncMock(
        return_value=ClaudeResponse(
            text='{"archetype":"portfolio","confidence":0.4,"reasoning":"r"}',
            input_tokens=100,
            output_tokens=20,
            cache_write_tokens=0,
            cache_read_tokens=1200,
            model="claude-sonnet-4-6",
            cost_usd=0.001,
        )
    )
    out = await classify_submission(
        claude=client,
        industry="x",
        brand_name="y",
        questionnaire={},
    )
    assert out.archetype == "service"  # forced fallback


async def test_classify_handles_garbage_json_via_retry():
    bad = ClaudeResponse(
        text="not json",
        input_tokens=10,
        output_tokens=2,
        cache_write_tokens=0,
        cache_read_tokens=0,
        model="claude-sonnet-4-6",
        cost_usd=0,
    )
    good = ClaudeResponse(
        text='{"archetype":"service","confidence":0.7,"reasoning":""}',
        input_tokens=10,
        output_tokens=10,
        cache_write_tokens=0,
        cache_read_tokens=0,
        model="claude-sonnet-4-6",
        cost_usd=0,
    )
    client = AsyncMock()
    client.complete_json = AsyncMock(side_effect=[bad, good])
    out = await classify_submission(
        claude=client,
        industry="x",
        brand_name="y",
        questionnaire={},
    )
    assert out.archetype == "service"
    assert client.complete_json.await_count == 2
