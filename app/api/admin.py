from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status

from app.db import db
from app.settings import settings

router = APIRouter()


def _auth(authorization: str | None) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.admin_bearer_token:
        raise HTTPException(status_code=401, detail="invalid token")


@router.post("/api/admin/jobs/{job_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_job(
    job_id: UUID,
    background: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict:
    _auth(authorization)
    job = await db.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    await db.update_job_status(
        job_id,
        "queued",
        progress_pct=0,
        error_code=None,
        error_message=None,
    )

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
    return {"job_id": str(job_id), "status": "queued"}
