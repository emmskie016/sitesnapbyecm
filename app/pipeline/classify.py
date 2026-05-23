from __future__ import annotations

import json
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from app.integrations.anthropic_client import MODEL_PRIMARY, ClaudeClient
from app.models import ClassifyOutput

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "system_classifier.md"


def _system_blocks() -> list[dict]:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def _user_text(industry: str, brand_name: str, questionnaire: dict) -> str:
    return (
        f"Brand name: {brand_name}\n"
        f"Industry / niche: {industry}\n"
        f"Questionnaire JSON: {json.dumps(questionnaire, ensure_ascii=False)}\n\n"
        f"Return the JSON object."
    )


def _extract_json(text: str) -> dict:
    # strip code fences if present, find first { ... }
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json") :]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return json.loads(cleaned[start : end + 1])


async def classify_submission(
    *,
    claude: ClaudeClient,
    industry: str,
    brand_name: str,
    questionnaire: dict,
) -> ClassifyOutput:
    sys_blocks = _system_blocks()
    user = _user_text(industry, brand_name, questionnaire)

    for attempt in range(2):
        resp = await claude.complete_json(
            system_blocks=sys_blocks,
            user_text=user,
            max_tokens=200,
            model=MODEL_PRIMARY,
            temperature=0.2,
        )
        try:
            data = _extract_json(resp.text)
            parsed = ClassifyOutput.model_validate(data)
            if parsed.confidence < 0.6:
                logger.info("classify low-confidence ({}); forcing service", parsed.confidence)
                return ClassifyOutput(
                    archetype="service",
                    confidence=parsed.confidence,
                    reasoning=parsed.reasoning + " (forced default)",
                )
            return parsed
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("classify attempt {} parse failed: {}", attempt + 1, e)
            user += "\n\nReminder: return JSON only, no prose."
    return ClassifyOutput(archetype="service", confidence=0.0, reasoning="parse_failed")
