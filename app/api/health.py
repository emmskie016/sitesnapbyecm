from __future__ import annotations

from fastapi import APIRouter

from app.db import db
from app.settings import settings

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    deps = {
        "claude": "configured" if settings.anthropic_api_key else "missing",
        "supabase": "connected" if (db.pool is not None) else "disconnected",
        "r2": "configured" if settings.r2_access_key_id else "missing",
        "unsplash": "configured" if settings.unsplash_access_key else "missing",
        "resend": "configured" if settings.resend_api_key else "missing",
    }
    overall = "ok" if all(v in ("configured", "connected") for v in deps.values()) else "degraded"
    return {"status": overall, "dependencies": deps, "env": settings.env}
