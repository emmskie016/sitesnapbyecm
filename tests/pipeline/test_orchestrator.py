from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.integrations.unsplash_client import UnsplashPhoto
from app.models import ClassifyOutput, CopyOutput
from app.pipeline.orchestrator import generate_site


VALID_COPY = CopyOutput.model_validate(
    {
        "headline": "h",
        "subheadline": "s",
        "primary_cta": "p",
        "secondary_cta": "s",
        "about": {"heading": "h", "body": "b"},
        "features": [
            {"icon": "leaf", "title": "a", "body": "x"},
            {"icon": "clock", "title": "b", "body": "y"},
            {"icon": "heart", "title": "c", "body": "z"},
        ],
        "social_proof": [{"text": "t", "author": "A B."}],
        "footer_tagline": "f",
        "meta": {"title": "t", "description": "d", "keywords": []},
        "palette_hint": "warm-earth",
    }
)


def _make_deps():
    db = AsyncMock()
    db.fetch_job = AsyncMock(
        return_value={
            "id": "job1",
            "submission_id": "sub1",
            "attempts": 0,
            "status": "queued",
            "claude_tokens_in": 0,
            "claude_tokens_out": 0,
            "claude_cost_usd": 0,
        }
    )
    db.fetch_submission = AsyncMock(
        return_value={
            "id": "sub1",
            "full_name": "Jane Doe",
            "email": "j@x.com",
            "brand_name": "Bloom",
            "industry": "florist",
            "questionnaire": {},
        }
    )
    db.update_job_status = AsyncMock()
    db.add_claude_usage = AsyncMock()
    db.increment_attempts = AsyncMock(return_value=1)
    db.slug_exists = AsyncMock(return_value=False)

    classify = AsyncMock(
        return_value=ClassifyOutput(archetype="service", confidence=0.9, reasoning="")
    )
    copy_fn = AsyncMock(return_value=VALID_COPY)
    fetch_imgs = AsyncMock(
        return_value={
            slot: UnsplashPhoto("p", "r", "reg", "s", "a", "pg")
            for slot in ("hero", "feature_1", "feature_2", "feature_3")
        }
    )
    publish = AsyncMock(return_value="https://bloom-x7k2.sitesnap.app")
    notify = AsyncMock()

    return {
        "db": db,
        "classify": classify,
        "copy_fn": copy_fn,
        "fetch_imgs": fetch_imgs,
        "publish": publish,
        "notify": notify,
    }


async def test_orchestrator_walks_all_stages_to_done(monkeypatch):
    deps = _make_deps()
    monkeypatch.setattr("app.pipeline.orchestrator.classify_submission", deps["classify"])
    monkeypatch.setattr("app.pipeline.orchestrator.write_copy", deps["copy_fn"])
    monkeypatch.setattr("app.pipeline.orchestrator.fetch_images_for_archetype", deps["fetch_imgs"])
    monkeypatch.setattr("app.pipeline.orchestrator.publish_site", deps["publish"])
    monkeypatch.setattr("app.pipeline.orchestrator.notify_customer_and_operator", deps["notify"])

    job_id = uuid4()
    await generate_site(
        job_id,
        db=deps["db"],
        claude=MagicMock(),
        unsplash=MagicMock(),
        r2=MagicMock(),
        http=MagicMock(),
        resend=MagicMock(),
    )

    statuses = [c.args[1] for c in deps["db"].update_job_status.await_args_list]
    assert "classifying" in statuses
    assert "writing_copy" in statuses
    assert "fetching_images" in statuses
    assert "rendering" in statuses
    assert "publishing" in statuses
    assert "notifying" in statuses
    assert statuses[-1] == "done"


async def test_orchestrator_marks_failed_on_unrecoverable_error(monkeypatch):
    from app.pipeline.copy import CopyInvalidSchema

    deps = _make_deps()
    deps["copy_fn"].side_effect = CopyInvalidSchema("bad")
    monkeypatch.setattr("app.pipeline.orchestrator.classify_submission", deps["classify"])
    monkeypatch.setattr("app.pipeline.orchestrator.write_copy", deps["copy_fn"])
    monkeypatch.setattr("app.pipeline.orchestrator.fetch_images_for_archetype", deps["fetch_imgs"])
    monkeypatch.setattr("app.pipeline.orchestrator.publish_site", deps["publish"])
    monkeypatch.setattr("app.pipeline.orchestrator.notify_customer_and_operator", deps["notify"])

    job_id = uuid4()
    await generate_site(
        job_id,
        db=deps["db"],
        claude=MagicMock(),
        unsplash=MagicMock(),
        r2=MagicMock(),
        http=MagicMock(),
        resend=MagicMock(),
    )

    statuses = [c.args[1] for c in deps["db"].update_job_status.await_args_list]
    assert statuses[-1] == "failed"
    last_kwargs = deps["db"].update_job_status.await_args_list[-1].kwargs
    assert last_kwargs["error_code"] == "copy_invalid_schema"
