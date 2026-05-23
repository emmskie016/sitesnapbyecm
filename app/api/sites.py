from __future__ import annotations

import hashlib
import time
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel

from app.db import db
from app.models import Submission

router = APIRouter()


class SiteCreated(BaseModel):
    job_id: UUID
    status_url: str


class JobView(BaseModel):
    job_id: UUID
    status: str
    progress_pct: int
    site_url: str | None
    error: dict | None


def _request_hash(email: str, brand_name: str) -> str:
    bucket = int(time.time() // 60)
    raw = f"{email.lower()}|{brand_name.lower()}|{bucket}".encode()
    return hashlib.sha256(raw).hexdigest()


@router.post("/api/sites", response_model=SiteCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_site(
    submission: Submission,
    background: BackgroundTasks,
    request: Request,
) -> SiteCreated:
    rh = _request_hash(submission.email, submission.brand_name)
    sub_id = await db.insert_submission(
        full_name=submission.full_name,
        email=submission.email,
        brand_name=submission.brand_name,
        industry=submission.industry,
        questionnaire=submission.questionnaire,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_hash=rh,
    )
    job_id = await db.insert_job(sub_id)

    # Lazy import + lazy client construction so tests don't need real keys.
    from app.integrations.anthropic_client import claude
    from app.integrations.r2_client import r2
    from app.integrations.resend_client import resend_client
    from app.integrations.unsplash_client import unsplash
    from app.pipeline.orchestrator import generate_site

    async def _run() -> None:
        async with httpx.AsyncClient() as http:
            await generate_site(
                job_id,
                db=db,
                claude=claude,
                unsplash=unsplash,
                r2=r2,
                http=http,
                resend=resend_client,
            )

    background.add_task(_run)
    return SiteCreated(job_id=job_id, status_url=f"/status/{job_id}")


@router.get("/api/jobs/{job_id}", response_model=JobView)
async def get_job(job_id: UUID) -> JobView:
    row = await db.fetch_job(job_id)
    if not row:
        raise HTTPException(status_code=404, detail="job not found")
    error = None
    if row.get("error_code") or row.get("error_message"):
        error = {"code": row.get("error_code"), "message": row.get("error_message")}
    return JobView(
        job_id=job_id,
        status=row["status"],
        progress_pct=row["progress_pct"],
        site_url=row.get("site_url"),
        error=error,
    )
