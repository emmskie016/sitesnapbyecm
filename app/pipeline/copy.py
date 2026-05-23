from __future__ import annotations

import json
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from app.integrations.anthropic_client import (
    MODEL_FALLBACK,
    MODEL_PRIMARY,
    ClaudeClient,
)
from app.models import CopyOutput
from app.pipeline.classify import _extract_json

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


class CopyInvalidSchema(Exception):
    """Both sonnet and opus failed to produce schema-valid copy."""


def _system_blocks(archetype: str) -> list[dict]:
    sys_md = (PROMPTS_DIR / "system_copywriter.md").read_text(encoding="utf-8")
    arch_md = (PROMPTS_DIR / f"archetype_{archetype}.md").read_text(encoding="utf-8")
    return [
        {"type": "text", "text": sys_md, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": arch_md, "cache_control": {"type": "ephemeral"}},
    ]


def _user_text(submission: dict, archetype: str) -> str:
    return (
        f"Archetype assigned: {archetype}\n"
        f"Brand: {submission['brand_name']}\n"
        f"Industry: {submission['industry']}\n"
        f"Questionnaire: {json.dumps(submission.get('questionnaire', {}), ensure_ascii=False)}\n\n"
        f"Return the full JSON object matching the schema."
    )


async def write_copy(
    *,
    claude: ClaudeClient,
    archetype: str,
    submission: dict,
) -> CopyOutput:
    sys_blocks = _system_blocks(archetype)
    user = _user_text(submission, archetype)

    attempts = [
        {"model": MODEL_PRIMARY, "temperature": 0.7},
        {"model": MODEL_PRIMARY, "temperature": 0.3},
        {"model": MODEL_FALLBACK, "temperature": 0.4},
    ]
    last_err: Exception | None = None
    for i, cfg in enumerate(attempts):
        try:
            resp = await claude.complete_json(
                system_blocks=sys_blocks,
                user_text=user
                if i == 0
                else user + "\n\nReturn JSON only, matching the schema exactly. No prose.",
                max_tokens=1500,
                model=cfg["model"],
                temperature=cfg["temperature"],
            )
            data = _extract_json(resp.text)
            return CopyOutput.model_validate(data)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("copy attempt {} ({}) failed: {}", i + 1, cfg["model"], e)
            last_err = e
    raise CopyInvalidSchema(str(last_err))
