from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.settings import settings

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

router = APIRouter()


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


@router.get("/status/{job_id}", response_class=HTMLResponse)
async def status_page(job_id: UUID) -> HTMLResponse:
    template = _env().get_template("status.html.j2")
    html = template.render(
        job_id=str(job_id),
        contact_email=settings.resend_operator_email,
    )
    return HTMLResponse(content=html)
