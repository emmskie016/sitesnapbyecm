from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import httpx
from loguru import logger

from app.db import DB
from app.integrations.anthropic_client import ClaudeClient
from app.integrations.r2_client import R2Client
from app.integrations.resend_client import ResendClient
from app.integrations.unsplash_client import UnsplashClient
from app.models import STATUS_PROGRESS, JobStatus
from app.pipeline.classify import classify_submission
from app.pipeline.copy import CopyInvalidSchema, write_copy
from app.pipeline.images import fetch_images_for_archetype
from app.pipeline.notify import notify_customer_and_operator
from app.pipeline.publish import publish_site
from app.pipeline.render import render_site
from app.slugs import generate_slug

MAX_SLUG_ATTEMPTS = 5


class SlugCollision(Exception):
    pass


def _classify_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, CopyInvalidSchema):
        return "copy_invalid_schema", str(exc)
    if isinstance(exc, SlugCollision):
        return "slug_collision", str(exc)
    name = type(exc).__name__.lower()
    if "ratelimit" in name:
        return "claude_rate_limit", str(exc)
    return "unknown", repr(exc)


async def _set_status(db: DB, job_id: UUID, status: JobStatus, **extra) -> None:
    pct = STATUS_PROGRESS.get(status, 0)
    await db.update_job_status(job_id, status.value, progress_pct=pct, **extra)


async def generate_site(
    job_id: UUID,
    *,
    db: DB,
    claude: ClaudeClient,
    unsplash: UnsplashClient,
    r2: R2Client,
    http: httpx.AsyncClient,
    resend: ResendClient,
) -> None:
    job = await db.fetch_job(job_id)
    if not job:
        logger.error("orchestrator: job {} not found", job_id)
        return
    submission = await db.fetch_submission(job["submission_id"])
    if not submission:
        await _set_status(
            db,
            job_id,
            JobStatus.FAILED,
            error_code="submission_missing",
            error_message="submission row gone",
        )
        return

    await db.update_job_status(job_id, JobStatus.QUEUED.value, started_at_now=True)

    try:
        # Stage 1
        await _set_status(db, job_id, JobStatus.CLASSIFYING)
        classification = await classify_submission(
            claude=claude,
            industry=submission["industry"],
            brand_name=submission["brand_name"],
            questionnaire=submission["questionnaire"] or {},
        )
        archetype = classification.archetype

        # Stage 2
        await _set_status(db, job_id, JobStatus.WRITING_COPY, archetype=archetype)
        copy = await write_copy(claude=claude, archetype=archetype, submission=submission)

        # Stage 3
        await _set_status(db, job_id, JobStatus.FETCHING_IMAGES)
        images = await fetch_images_for_archetype(
            archetype=archetype,
            industry=submission["industry"],
            unsplash=unsplash,
            db=db,
        )

        # Stage 4: render in-process
        await _set_status(db, job_id, JobStatus.RENDERING)
        # Generate a slug with collision retries.
        slug: str | None = None
        for _ in range(MAX_SLUG_ATTEMPTS):
            candidate = generate_slug(submission["brand_name"])
            if not await db.slug_exists(candidate, exclude_job_id=job_id):
                slug = candidate
                break
        if slug is None:
            raise SlugCollision("could not generate a unique slug in 5 attempts")

        rendered = render_site(
            archetype=archetype,
            brand_name=submission["brand_name"],
            slug=slug,
            copy=copy,
            images=images,
            now=datetime.now(timezone.utc),
        )

        # Stage 5
        await _set_status(db, job_id, JobStatus.PUBLISHING, slug=slug, palette=rendered.palette)
        site_url = await publish_site(
            slug=slug,
            html=rendered.html,
            assets=rendered.assets_to_download,
            r2=r2,
            http=http,
        )

        # Stage 6
        await _set_status(db, job_id, JobStatus.NOTIFYING, site_url=site_url)
        await notify_customer_and_operator(
            resend=resend,
            customer_email=submission["email"],
            customer_name=submission["full_name"],
            brand_name=submission["brand_name"],
            site_url=site_url,
            archetype=archetype,
            tokens_in=job.get("claude_tokens_in", 0),
            tokens_out=job.get("claude_tokens_out", 0),
            cost_usd=float(job.get("claude_cost_usd", 0) or 0),
            slug=slug,
        )

        await _set_status(db, job_id, JobStatus.DONE, finished_at_now=True)
        logger.info("orchestrator: job {} done at {}", job_id, site_url)

    except Exception as exc:
        code, msg = _classify_error(exc)
        await db.increment_attempts(job_id)
        await _set_status(
            db,
            job_id,
            JobStatus.FAILED,
            error_code=code,
            error_message=msg,
            finished_at_now=True,
        )
        logger.exception("orchestrator: job {} failed: code={} msg={}", job_id, code, msg)
