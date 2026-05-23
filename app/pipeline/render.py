from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.integrations.unsplash_client import UnsplashPhoto
from app.models import CopyOutput
from app.palettes import get_palette

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


@dataclass
class RenderedSite:
    html: str
    palette: dict[str, str]
    assets_to_download: dict[str, str]  # local_filename -> source URL


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_site(
    *,
    archetype: str,
    brand_name: str,
    slug: str,
    copy: CopyOutput,
    images: dict[str, UnsplashPhoto],
    now: datetime,
) -> RenderedSite:
    palette = get_palette(archetype, copy.palette_hint)
    assets: dict[str, str] = {}

    image_ctx: dict[str, dict[str, str]] = {}
    for slot, photo in images.items():
        local_name = f"assets/{slot}.jpg"
        assets[local_name] = photo.url_regular
        image_ctx[slot] = {
            "local": local_name,
            "attribution": photo.attribution_html,
        }

    env = _env()
    template = env.get_template(f"{archetype}/index.html.j2")
    html = template.render(
        brand={"name": brand_name, "slug": slug},
        copy=copy.model_dump(),
        palette=palette,
        images=image_ctx,
        now=now,
    )
    return RenderedSite(html=html, palette=palette, assets_to_download=assets)
