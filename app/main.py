from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import admin, health, sites, status
from app.db import db
from app.settings import settings

# Configure logging once at import time.
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    serialize=True,  # JSON output for Render log collector
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.env != "test":
        await db.connect()
    logger.info("app started env={}", settings.env)
    try:
        yield
    finally:
        if settings.env != "test":
            await db.disconnect()
        logger.info("app stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="SiteSnap Backend", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        # Static allowlist for known production origins.
        allow_origins=[
            "https://sitesnapbyecm.lovable.app",
            "https://sitesnap.app",
            "https://emmersonmorales.com",
            "https://sites.emmersonmorales.com",
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        # Regex catches Lovable's preview origins (id-preview-xxx.lovable.app,
        # *.lovableproject.com), plus any future *.emmersonmorales.com
        # subdomain we point at this backend.
        allow_origin_regex=(
            r"^https://([a-z0-9-]+\.)*lovable\.app$"
            r"|^https://([a-z0-9-]+\.)*lovableproject\.com$"
            r"|^https://([a-z0-9-]+\.)*emmersonmorales\.com$"
        ),
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["content-type", "authorization"],
    )
    app.include_router(sites.router)
    app.include_router(status.router)
    app.include_router(health.router)
    app.include_router(admin.router)
    return app


app = create_app()
