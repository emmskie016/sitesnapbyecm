from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.anthropic_client import ClaudeClient, ClaudeResponse


@pytest.fixture
def fake_sdk_response():
    resp = MagicMock()
    resp.content = [MagicMock(text='{"archetype":"service","confidence":0.9,"reasoning":"x"}')]
    resp.usage = MagicMock(
        input_tokens=120,
        output_tokens=40,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=1500,
    )
    resp.stop_reason = "end_turn"
    resp.model = "claude-sonnet-4-6"
    return resp


async def test_call_claude_returns_text_and_usage(fake_sdk_response, monkeypatch):
    fake_messages = MagicMock()
    fake_messages.create = AsyncMock(return_value=fake_sdk_response)
    fake_client = MagicMock(messages=fake_messages)

    client = ClaudeClient(sdk_client=fake_client)
    result = await client.complete_json(
        system_blocks=[{"type": "text", "text": "SYSTEM"}],
        user_text="USER",
        max_tokens=400,
    )
    assert isinstance(result, ClaudeResponse)
    assert "service" in result.text
    assert result.input_tokens == 120
    assert result.output_tokens == 40
    assert result.cache_read_tokens == 1500


async def test_call_claude_propagates_rate_limit(monkeypatch):
    import anthropic

    fake_messages = MagicMock()
    fake_messages.create = AsyncMock(
        side_effect=anthropic.RateLimitError("rl", response=MagicMock(status_code=429), body=None)
    )
    fake_client = MagicMock(messages=fake_messages)

    client = ClaudeClient(sdk_client=fake_client)
    with pytest.raises(anthropic.RateLimitError):
        await client.complete_json(system_blocks=[], user_text="x", max_tokens=10)
