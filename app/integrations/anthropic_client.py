from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic

from app.settings import settings

MODEL_PRIMARY = "claude-sonnet-4-6"
MODEL_FALLBACK = "claude-opus-4-7"

PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
}


@dataclass
class ClaudeResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    model: str
    cost_usd: float


def compute_cost(model: str, *, input_t: int, output_t: int, cw_t: int, cr_t: int) -> float:
    p = PRICING.get(model, PRICING[MODEL_PRIMARY])
    return (
        input_t * p["input"]
        + output_t * p["output"]
        + cw_t * p["cache_write"]
        + cr_t * p["cache_read"]
    ) / 1_000_000


class ClaudeClient:
    def __init__(self, sdk_client: Any | None = None) -> None:
        self.sdk = sdk_client or AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete_json(
        self,
        *,
        system_blocks: list[dict[str, Any]],
        user_text: str,
        max_tokens: int,
        model: str = MODEL_PRIMARY,
        temperature: float = 0.7,
    ) -> ClaudeResponse:
        resp = await self.sdk.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_blocks,
            messages=[{"role": "user", "content": user_text}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        usage = resp.usage
        in_t = getattr(usage, "input_tokens", 0)
        out_t = getattr(usage, "output_tokens", 0)
        cw_t = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cr_t = getattr(usage, "cache_read_input_tokens", 0) or 0
        cost = compute_cost(model, input_t=in_t, output_t=out_t, cw_t=cw_t, cr_t=cr_t)
        return ClaudeResponse(
            text=text,
            input_tokens=in_t,
            output_tokens=out_t,
            cache_write_tokens=cw_t,
            cache_read_tokens=cr_t,
            model=resp.model,
            cost_usd=cost,
        )


claude = ClaudeClient()
