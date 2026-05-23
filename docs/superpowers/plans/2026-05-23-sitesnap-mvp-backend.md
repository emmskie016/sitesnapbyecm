# SiteSnap MVP Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python FastAPI backend that takes a SiteSnap form submission and produces a live, hosted single-page website within ~60 seconds, with the live URL emailed to the customer.

**Architecture:** FastAPI service on Render with Supabase Postgres for state. Form intake returns 202 + status URL; an in-process `BackgroundTask` runs the 6-stage generation pipeline (classify → write copy → fetch images → render → publish → notify). Generated sites upload to Cloudflare R2 and serve at `<slug>.sitesnap.app` via a thin Cloudflare Worker. Three hand-designed archetype templates (service / hospitality / portfolio) with 12 curated palettes; Claude Sonnet 4.6 writes copy; Unsplash supplies photography.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, Pydantic v2, asyncpg, anthropic, aioboto3 (R2), httpx, Pillow, Jinja2, Resend, pytest + pytest-asyncio + respx, ruff, Cloudflare Workers (TypeScript), Wrangler.

**Spec:** `docs/superpowers/specs/2026-05-23-sitesnap-mvp-backend-design.md`

---

## File map

Files created by this plan, grouped by responsibility:

```
sitesnap-backend/
├── pyproject.toml                              # T1
├── .env.example                                # T1
├── Dockerfile                                  # T33
├── render.yaml                                 # T33
├── README.md                                   # T33
├── app/
│   ├── __init__.py                             # T1
│   ├── main.py                                 # T31
│   ├── settings.py                             # T2
│   ├── slugs.py                                # T3
│   ├── palettes.py                             # T4
│   ├── models.py                               # T5
│   ├── db.py                                   # T7
│   ├── api/
│   │   ├── __init__.py                         # T1
│   │   ├── sites.py                            # T27
│   │   ├── status.py                           # T28
│   │   ├── health.py                           # T29
│   │   └── admin.py                            # T30
│   ├── integrations/
│   │   ├── __init__.py                         # T1
│   │   ├── anthropic_client.py                 # T8
│   │   ├── unsplash_client.py                  # T9, T12
│   │   ├── r2_client.py                        # T10
│   │   └── resend_client.py                    # T11
│   └── pipeline/
│       ├── __init__.py                         # T1
│       ├── classify.py                         # T20
│       ├── copy.py                             # T21
│       ├── images.py                           # T22
│       ├── render.py                           # T23
│       ├── publish.py                          # T24
│       ├── notify.py                           # T25
│       └── orchestrator.py                     # T26
├── prompts/
│   ├── system_classifier.md                    # T13
│   ├── system_copywriter.md                    # T14
│   ├── archetype_service.md                    # T15
│   ├── archetype_hospitality.md                # T15
│   └── archetype_portfolio.md                  # T15
├── templates/
│   ├── service/{index.html.j2, styles.css.j2, manifest.json}     # T16
│   ├── hospitality/{index.html.j2, styles.css.j2, manifest.json} # T17
│   ├── portfolio/{index.html.j2, styles.css.j2, manifest.json}   # T18
│   └── status.html.j2                          # T19
├── migrations/
│   ├── 0001_init.sql                           # T6
│   └── 0002_unsplash_cache.sql                 # T12
├── tests/
│   ├── conftest.py                             # T1
│   ├── unit/test_slugs.py                      # T3
│   ├── unit/test_palettes.py                   # T4
│   ├── unit/test_models.py                     # T5
│   ├── integrations/test_anthropic_client.py   # T8
│   ├── integrations/test_unsplash_client.py    # T9, T12
│   ├── integrations/test_r2_client.py          # T10
│   ├── integrations/test_resend_client.py      # T11
│   ├── pipeline/test_classify.py               # T20
│   ├── pipeline/test_copy.py                   # T21
│   ├── pipeline/test_images.py                 # T22
│   ├── pipeline/test_render.py                 # T23
│   ├── pipeline/test_publish.py                # T24
│   ├── pipeline/test_notify.py                 # T25
│   ├── pipeline/test_orchestrator.py           # T26
│   ├── api/test_sites.py                       # T27
│   ├── api/test_status.py                      # T28
│   ├── api/test_health.py                      # T29
│   └── api/test_admin.py                       # T30
└── infra/
    └── worker/
        ├── src/index.ts                        # T32
        ├── wrangler.toml                       # T32
        └── README.md                           # T32
```

---

## Conventions used in every task

- **TDD:** failing test first, run to confirm fail, minimal impl, run to confirm pass, commit.
- **Commits:** Conventional commits — `feat:`, `test:`, `chore:`, `docs:`. Always small.
- **Run commands** assume CWD = `C:\Users\emmer\sitesnap-backend`.
- **Test runner:** `uv run pytest <path> -v`.
- **Lint/format:** `uv run ruff check . && uv run ruff format .` before each commit.
- **Async:** all I/O is `async`. Tests use `@pytest.mark.asyncio`.

---

## Phase 0 — Bootstrap

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`, `app/api/__init__.py`, `app/integrations/__init__.py`, `app/pipeline/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "sitesnap-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "pydantic-settings>=2.6",
  "httpx>=0.27",
  "anthropic>=0.40",
  "resend>=2.4",
  "aioboto3>=13.2",
  "pillow>=11",
  "jinja2>=3.1",
  "asyncpg>=0.30",
  "loguru>=0.7",
  "python-slugify>=8.0",
  "nanoid>=2.0",
  "python-multipart>=0.0.12",
]

[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "respx>=0.21",
  "ruff>=0.7",
  "pytest-postgresql>=6.1",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Write `.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
UNSPLASH_ACCESS_KEY=...
SUPABASE_DB_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=sitesnap-sites
R2_PUBLIC_BASE=https://sitesnap.app
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=hello@sitesnap.app
RESEND_OPERATOR_EMAIL=devops@branchlead.com
ADMIN_BEARER_TOKEN=change-me
SENTRY_DSN=
LOG_LEVEL=INFO
ENV=local
```

- [ ] **Step 3: Create empty package files**

Each of these is an empty file (`""`):
- `app/__init__.py`
- `app/api/__init__.py`
- `app/integrations/__init__.py`
- `app/pipeline/__init__.py`

- [ ] **Step 4: Write `tests/conftest.py`**

```python
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic")
os.environ.setdefault("UNSPLASH_ACCESS_KEY", "test-unsplash")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://localhost/test")
os.environ.setdefault("R2_ACCOUNT_ID", "test-account")
os.environ.setdefault("R2_ACCESS_KEY_ID", "test-key")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "test-secret")
os.environ.setdefault("R2_BUCKET", "test-bucket")
os.environ.setdefault("R2_PUBLIC_BASE", "https://test.sitesnap.app")
os.environ.setdefault("RESEND_API_KEY", "test-resend")
os.environ.setdefault("RESEND_FROM_EMAIL", "test@sitesnap.app")
os.environ.setdefault("RESEND_OPERATOR_EMAIL", "ops@sitesnap.app")
os.environ.setdefault("ADMIN_BEARER_TOKEN", "test-admin")
os.environ.setdefault("ENV", "test")


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 5: Install deps and verify**

```bash
uv sync
uv run python -c "import fastapi, anthropic, aioboto3, jinja2, asyncpg, resend; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example app tests
git commit -m "chore: project scaffolding (pyproject, env template, pkg layout)"
```

---

## Phase 1 — Foundation

### Task 2: Settings

**Files:**
- Create: `app/settings.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/__init__.py` (empty) and `tests/unit/test_settings.py`:

```python
from app.settings import settings


def test_settings_loads_from_env():
    assert settings.anthropic_api_key == "test-anthropic"
    assert settings.r2_bucket == "test-bucket"
    assert settings.env == "test"


def test_settings_has_defaults():
    assert settings.log_level == "INFO"
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/unit/test_settings.py -v
```

Expected: ImportError (`app.settings` doesn't exist).

- [ ] **Step 3: Implement `app/settings.py`**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    unsplash_access_key: str
    supabase_db_url: str

    r2_account_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str
    r2_public_base: str

    resend_api_key: str
    resend_from_email: str
    resend_operator_email: str

    admin_bearer_token: str

    sentry_dsn: str = ""
    log_level: str = "INFO"
    env: str = Field(default="local")


settings = Settings()
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/unit/test_settings.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/settings.py tests/unit/__init__.py tests/unit/test_settings.py
git commit -m "feat: settings loaded via pydantic-settings"
```

---

### Task 3: Slug generation

**Files:**
- Create: `app/slugs.py`
- Create: `tests/unit/test_slugs.py`

- [ ] **Step 1: Write the failing test**

```python
import re
from app.slugs import generate_slug


def test_slug_is_kebab_case_with_suffix():
    s = generate_slug("Bloom Florist!")
    assert re.fullmatch(r"bloom-florist-[a-z0-9]{4}", s)


def test_slug_handles_unicode_and_emoji():
    s = generate_slug("Cafe Ñoño 🌮")
    # python-slugify ASCII-folds Ñ→N, drops emoji
    assert s.startswith("cafe-nono-") and re.fullmatch(r"cafe-nono-[a-z0-9]{4}", s)


def test_slug_empty_brand_falls_back_to_site():
    s = generate_slug("   ")
    assert re.fullmatch(r"site-[a-z0-9]{4}", s)


def test_slug_truncates_long_brand():
    long = "A" * 200
    s = generate_slug(long)
    # base capped at 40 chars + "-" + 4-char suffix
    base, _, suffix = s.rpartition("-")
    assert len(base) <= 40
    assert re.fullmatch(r"[a-z0-9]{4}", suffix)
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/unit/test_slugs.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/slugs.py`**

```python
from nanoid import generate as nano
from slugify import slugify

SUFFIX_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
SUFFIX_LEN = 4
BASE_MAX = 40


def generate_slug(brand_name: str) -> str:
    base = slugify(brand_name or "", max_length=BASE_MAX, word_boundary=True) or "site"
    suffix = nano(SUFFIX_ALPHABET, SUFFIX_LEN)
    return f"{base}-{suffix}"
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/unit/test_slugs.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/slugs.py tests/unit/test_slugs.py
git commit -m "feat: slug generator with collision-resistant 4-char suffix"
```

---

### Task 4: Curated palettes

**Files:**
- Create: `app/palettes.py`
- Create: `tests/unit/test_palettes.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from app.palettes import PALETTE_HINTS, get_palette


def test_each_archetype_has_four_palettes():
    for arch in ("service", "hospitality", "portfolio"):
        assert len(PALETTE_HINTS[arch]) == 4


def test_palette_returns_full_token_set():
    p = get_palette("service", "warm-earth")
    assert set(p.keys()) == {"primary", "accent", "neutral_bg", "neutral_surface", "ink", "ink_soft"}
    for v in p.values():
        assert v.startswith("#") and len(v) == 7


def test_palette_unknown_hint_falls_back_to_first():
    p_first = get_palette("service", PALETTE_HINTS["service"][0])
    p_unknown = get_palette("service", "nope-not-a-hint")
    assert p_first == p_unknown


def test_palette_unknown_archetype_raises():
    with pytest.raises(KeyError):
        get_palette("nonsense", "warm-earth")
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/unit/test_palettes.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/palettes.py`**

```python
"""Hand-curated palettes per archetype. 4 per archetype × 3 archetypes = 12 visual identities.

Hex values are picked, not LLM-generated, to guarantee a tasteful baseline.
"""

PALETTES: dict[str, dict[str, dict[str, str]]] = {
    "service": {
        "warm-earth": {
            "primary": "#8B5A3C",
            "accent": "#D4A574",
            "neutral_bg": "#FAF6F1",
            "neutral_surface": "#FFFFFF",
            "ink": "#2A1F18",
            "ink_soft": "#5C4A3D",
        },
        "cool-modern": {
            "primary": "#1E3A8A",
            "accent": "#38BDF8",
            "neutral_bg": "#F8FAFC",
            "neutral_surface": "#FFFFFF",
            "ink": "#0F172A",
            "ink_soft": "#475569",
        },
        "bold-vibrant": {
            "primary": "#9333EA",
            "accent": "#F59E0B",
            "neutral_bg": "#FAFAFA",
            "neutral_surface": "#FFFFFF",
            "ink": "#18181B",
            "ink_soft": "#52525B",
        },
        "muted-elegant": {
            "primary": "#374151",
            "accent": "#A78BFA",
            "neutral_bg": "#F9FAFB",
            "neutral_surface": "#FFFFFF",
            "ink": "#111827",
            "ink_soft": "#4B5563",
        },
    },
    "hospitality": {
        "warm-earth": {
            "primary": "#7C2D12",
            "accent": "#F59E0B",
            "neutral_bg": "#FEF8F0",
            "neutral_surface": "#FFFFFF",
            "ink": "#27150C",
            "ink_soft": "#6B4226",
        },
        "cool-modern": {
            "primary": "#0F766E",
            "accent": "#FBBF24",
            "neutral_bg": "#F0FDFA",
            "neutral_surface": "#FFFFFF",
            "ink": "#042F2E",
            "ink_soft": "#0D5F58",
        },
        "bold-vibrant": {
            "primary": "#DC2626",
            "accent": "#FACC15",
            "neutral_bg": "#FFFBEB",
            "neutral_surface": "#FFFFFF",
            "ink": "#1C1917",
            "ink_soft": "#57534E",
        },
        "muted-elegant": {
            "primary": "#1F2937",
            "accent": "#D4A574",
            "neutral_bg": "#F4F1EC",
            "neutral_surface": "#FFFFFF",
            "ink": "#111827",
            "ink_soft": "#4B5563",
        },
    },
    "portfolio": {
        "warm-earth": {
            "primary": "#451A03",
            "accent": "#EA580C",
            "neutral_bg": "#FFFBF5",
            "neutral_surface": "#FFFFFF",
            "ink": "#1C1917",
            "ink_soft": "#57534E",
        },
        "cool-modern": {
            "primary": "#0C0A09",
            "accent": "#06B6D4",
            "neutral_bg": "#FAFAF9",
            "neutral_surface": "#FFFFFF",
            "ink": "#0C0A09",
            "ink_soft": "#44403C",
        },
        "bold-vibrant": {
            "primary": "#000000",
            "accent": "#EAB308",
            "neutral_bg": "#FAFAFA",
            "neutral_surface": "#FFFFFF",
            "ink": "#000000",
            "ink_soft": "#404040",
        },
        "muted-elegant": {
            "primary": "#1E293B",
            "accent": "#94A3B8",
            "neutral_bg": "#F8FAFC",
            "neutral_surface": "#FFFFFF",
            "ink": "#0F172A",
            "ink_soft": "#475569",
        },
    },
}

PALETTE_HINTS: dict[str, list[str]] = {arch: list(p.keys()) for arch, p in PALETTES.items()}


def get_palette(archetype: str, hint: str) -> dict[str, str]:
    palettes = PALETTES[archetype]  # raises KeyError on unknown archetype
    if hint in palettes:
        return palettes[hint]
    return palettes[PALETTE_HINTS[archetype][0]]
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/unit/test_palettes.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/palettes.py tests/unit/test_palettes.py
git commit -m "feat: 12 hand-curated palettes (3 archetypes x 4 hints)"
```

---

### Task 5: Pydantic models

**Files:**
- Create: `app/models.py`
- Create: `tests/unit/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from pydantic import ValidationError
from app.models import CopyOutput, JobStatus, Submission


def test_submission_requires_core_fields():
    s = Submission(
        full_name="Jane Doe",
        email="jane@example.com",
        brand_name="Bloom",
        industry="florist",
        questionnaire={"tone": "warm"},
    )
    assert s.email == "jane@example.com"
    assert s.questionnaire["tone"] == "warm"


def test_submission_rejects_bad_email():
    with pytest.raises(ValidationError):
        Submission(full_name="J", email="not-an-email", brand_name="B", industry="i")


def test_copy_output_validates_full_schema():
    payload = {
        "headline": "Bloom in every season",
        "subheadline": "Hand-tied arrangements from local growers.",
        "primary_cta": "Order now",
        "secondary_cta": "See bouquets",
        "about": {"heading": "Our story", "body": "We started in 2019..."},
        "features": [
            {"icon": "leaf", "title": "Local", "body": "From growers within 50mi."},
            {"icon": "calendar", "title": "Daily", "body": "Cut every morning."},
            {"icon": "heart", "title": "Custom", "body": "We design to your vision."},
        ],
        "social_proof": [{"text": "Stunning.", "author": "Emma"}],
        "footer_tagline": "Made with love.",
        "meta": {"title": "Bloom Florist", "description": "Hand-tied bouquets.", "keywords": ["florist"]},
        "palette_hint": "warm-earth",
    }
    c = CopyOutput.model_validate(payload)
    assert len(c.features) == 3
    assert c.palette_hint == "warm-earth"


def test_copy_output_rejects_wrong_feature_count():
    payload = {
        "headline": "x", "subheadline": "x", "primary_cta": "x", "secondary_cta": "x",
        "about": {"heading": "x", "body": "x"},
        "features": [{"icon": "x", "title": "x", "body": "x"}],
        "social_proof": [],
        "footer_tagline": "x",
        "meta": {"title": "x", "description": "x", "keywords": []},
        "palette_hint": "warm-earth",
    }
    with pytest.raises(ValidationError):
        CopyOutput.model_validate(payload)


def test_job_status_string_enum():
    assert JobStatus.QUEUED.value == "queued"
    assert JobStatus.DONE.value == "done"
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/models.py`**

```python
from enum import Enum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

PaletteHint = Literal["warm-earth", "cool-modern", "bold-vibrant", "muted-elegant"]
Archetype = Literal["service", "hospitality", "portfolio"]


class Submission(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    brand_name: str = Field(min_length=1, max_length=200)
    industry: str = Field(min_length=1, max_length=200)
    questionnaire: dict = Field(default_factory=dict)


class JobStatus(str, Enum):
    QUEUED = "queued"
    CLASSIFYING = "classifying"
    WRITING_COPY = "writing_copy"
    FETCHING_IMAGES = "fetching_images"
    RENDERING = "rendering"
    PUBLISHING = "publishing"
    NOTIFYING = "notifying"
    DONE = "done"
    FAILED = "failed"


STATUS_PROGRESS: dict[JobStatus, int] = {
    JobStatus.QUEUED: 0,
    JobStatus.CLASSIFYING: 10,
    JobStatus.WRITING_COPY: 30,
    JobStatus.FETCHING_IMAGES: 50,
    JobStatus.RENDERING: 70,
    JobStatus.PUBLISHING: 90,
    JobStatus.NOTIFYING: 95,
    JobStatus.DONE: 100,
    JobStatus.FAILED: 0,
}


class AboutBlock(BaseModel):
    heading: str
    body: str


class FeatureBlock(BaseModel):
    icon: str
    title: str
    body: str


class SocialProof(BaseModel):
    text: str
    author: str


class MetaBlock(BaseModel):
    title: str
    description: str
    keywords: list[str] = Field(default_factory=list)


class CopyOutput(BaseModel):
    headline: str
    subheadline: str
    primary_cta: str
    secondary_cta: str
    about: AboutBlock
    features: list[FeatureBlock] = Field(min_length=3, max_length=3)
    social_proof: list[SocialProof]
    footer_tagline: str
    meta: MetaBlock
    palette_hint: PaletteHint


class ClassifyOutput(BaseModel):
    archetype: Archetype
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class ImageSlot(BaseModel):
    slot: str
    url: str
    photo_id: str
    attribution_html: str
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/unit/test_models.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/models.py tests/unit/test_models.py
git commit -m "feat: Pydantic models for submissions, jobs, copy output, status"
```

---

## Phase 2 — Database

### Task 6: Initial migration

**Files:**
- Create: `migrations/0001_init.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 0001_init.sql
create extension if not exists "pgcrypto";

create table submissions (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  full_name     text not null,
  email         text not null,
  brand_name    text not null,
  industry      text not null,
  questionnaire jsonb not null default '{}'::jsonb,
  ip            inet,
  user_agent    text,
  request_hash  text unique
);

create index submissions_email_idx on submissions(email, created_at desc);

create table jobs (
  id                 uuid primary key default gen_random_uuid(),
  submission_id      uuid not null references submissions(id) on delete cascade,
  status             text not null default 'queued',
  progress_pct       int  not null default 0,
  archetype          text,
  slug               text unique,
  palette            jsonb,
  site_url           text,
  error_code         text,
  error_message      text,
  attempts           int  not null default 0,
  claude_tokens_in   int  not null default 0,
  claude_tokens_out  int  not null default 0,
  claude_cost_usd    numeric(10,4) not null default 0,
  created_at         timestamptz not null default now(),
  started_at         timestamptz,
  finished_at        timestamptz,
  constraint jobs_status_chk check (status in (
    'queued','classifying','writing_copy','fetching_images',
    'rendering','publishing','notifying','done','failed'
  ))
);

create index jobs_active_idx
  on jobs(status, created_at)
  where status not in ('done','failed');
create index jobs_submission_idx on jobs(submission_id);
```

- [ ] **Step 2: Apply against local Postgres / dev Supabase**

If using Supabase CLI:

```bash
supabase db push
```

If hitting Supabase directly:

```bash
psql "$SUPABASE_DB_URL" -f migrations/0001_init.sql
```

Expected: no errors.

- [ ] **Step 3: Verify schema**

```bash
psql "$SUPABASE_DB_URL" -c "\d+ submissions" -c "\d+ jobs"
```

Expected: both tables listed with the columns shown above.

- [ ] **Step 4: Commit**

```bash
git add migrations/0001_init.sql
git commit -m "feat(db): initial schema for submissions and jobs"
```

---

### Task 7: Async DB client

**Files:**
- Create: `app/db.py`
- Create: `tests/integrations/__init__.py`, `tests/integrations/test_db.py`

- [ ] **Step 1: Write the failing test**

`tests/integrations/__init__.py` is empty. `tests/integrations/test_db.py`:

```python
import pytest
from app.db import DB


@pytest.mark.skipif("not __import__('os').environ.get('RUN_DB_TESTS')", reason="requires live DB")
async def test_db_roundtrip():
    db = DB()
    await db.connect()
    try:
        sub_id = await db.insert_submission(
            full_name="Test", email="t@example.com",
            brand_name="TestCo", industry="tech",
            questionnaire={"a": 1}, ip=None, user_agent="test", request_hash="hash-1",
        )
        assert sub_id

        job_id = await db.insert_job(sub_id)
        row = await db.fetch_job(job_id)
        assert row["status"] == "queued"

        await db.update_job_status(job_id, "classifying", progress_pct=10)
        row = await db.fetch_job(job_id)
        assert row["status"] == "classifying"
        assert row["progress_pct"] == 10
    finally:
        await db.disconnect()


def test_db_constructible_without_connect():
    db = DB()
    assert db.pool is None
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/integrations/test_db.py -v
```

Expected: ImportError on `app.db`. The DB roundtrip test is skipped unless `RUN_DB_TESTS=1`.

- [ ] **Step 3: Implement `app/db.py`**

```python
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
from loguru import logger

from app.settings import settings


class DB:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                settings.supabase_db_url,
                min_size=1,
                max_size=10,
                command_timeout=30,
            )
            logger.info("db pool connected")

    async def disconnect(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def insert_submission(
        self,
        *,
        full_name: str,
        email: str,
        brand_name: str,
        industry: str,
        questionnaire: dict[str, Any],
        ip: str | None,
        user_agent: str | None,
        request_hash: str,
    ) -> UUID:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            """
            insert into submissions (full_name, email, brand_name, industry, questionnaire, ip, user_agent, request_hash)
            values ($1, $2, $3, $4, $5::jsonb, $6::inet, $7, $8)
            on conflict (request_hash) do update set request_hash = excluded.request_hash
            returning id
            """,
            full_name, email, brand_name, industry,
            json.dumps(questionnaire), ip, user_agent, request_hash,
        )
        return row["id"]

    async def insert_job(self, submission_id: UUID) -> UUID:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            "insert into jobs (submission_id) values ($1) returning id",
            submission_id,
        )
        return row["id"]

    async def fetch_job(self, job_id: UUID) -> dict[str, Any] | None:
        assert self.pool is not None
        row = await self.pool.fetchrow("select * from jobs where id = $1", job_id)
        return dict(row) if row else None

    async def fetch_submission(self, submission_id: UUID) -> dict[str, Any] | None:
        assert self.pool is not None
        row = await self.pool.fetchrow("select * from submissions where id = $1", submission_id)
        return dict(row) if row else None

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        *,
        progress_pct: int | None = None,
        archetype: str | None = None,
        slug: str | None = None,
        palette: dict | None = None,
        site_url: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        started_at_now: bool = False,
        finished_at_now: bool = False,
    ) -> None:
        assert self.pool is not None
        sets = ["status = $2"]
        params: list[Any] = [job_id, status]

        def add(field: str, value: Any) -> None:
            params.append(value)
            sets.append(f"{field} = ${len(params)}")

        if progress_pct is not None:
            add("progress_pct", progress_pct)
        if archetype is not None:
            add("archetype", archetype)
        if slug is not None:
            add("slug", slug)
        if palette is not None:
            add("palette", json.dumps(palette))
            sets[-1] = f"palette = ${len(params)}::jsonb"
        if site_url is not None:
            add("site_url", site_url)
        if error_code is not None:
            add("error_code", error_code)
        if error_message is not None:
            add("error_message", error_message)
        if started_at_now:
            sets.append("started_at = coalesce(started_at, now())")
        if finished_at_now:
            sets.append("finished_at = now()")

        await self.pool.execute(
            f"update jobs set {', '.join(sets)} where id = $1",
            *params,
        )

    async def increment_attempts(self, job_id: UUID) -> int:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            "update jobs set attempts = attempts + 1 where id = $1 returning attempts",
            job_id,
        )
        return row["attempts"]

    async def slug_exists(self, slug: str, *, exclude_job_id: UUID | None = None) -> bool:
        assert self.pool is not None
        if exclude_job_id is not None:
            row = await self.pool.fetchval(
                "select 1 from jobs where slug = $1 and id <> $2 limit 1",
                slug, exclude_job_id,
            )
        else:
            row = await self.pool.fetchval(
                "select 1 from jobs where slug = $1 limit 1", slug,
            )
        return row is not None

    async def add_claude_usage(
        self, job_id: UUID, *, tokens_in: int, tokens_out: int, cost_usd: float
    ) -> None:
        assert self.pool is not None
        await self.pool.execute(
            """
            update jobs
            set claude_tokens_in = claude_tokens_in + $2,
                claude_tokens_out = claude_tokens_out + $3,
                claude_cost_usd = claude_cost_usd + $4
            where id = $1
            """,
            job_id, tokens_in, tokens_out, cost_usd,
        )


db = DB()
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/integrations/test_db.py -v
```

Expected: 1 passed, 1 skipped (the live roundtrip test).

- [ ] **Step 5: (Optional) Live roundtrip with dev Supabase**

```bash
RUN_DB_TESTS=1 SUPABASE_DB_URL="<your dev db url>" uv run pytest tests/integrations/test_db.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/db.py tests/integrations/__init__.py tests/integrations/test_db.py
git commit -m "feat(db): async asyncpg client with submission and job ops"
```

---

## Phase 3 — Integrations

### Task 8: Anthropic client (Claude)

**Files:**
- Create: `app/integrations/anthropic_client.py`
- Create: `tests/integrations/test_anthropic_client.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.anthropic_client import ClaudeClient, ClaudeResponse


@pytest.fixture
def fake_sdk_response():
    resp = MagicMock()
    resp.content = [MagicMock(text='{"archetype":"service","confidence":0.9,"reasoning":"x"}')]
    resp.usage = MagicMock(input_tokens=120, output_tokens=40,
                           cache_creation_input_tokens=0, cache_read_input_tokens=1500)
    resp.stop_reason = "end_turn"
    resp.model = "claude-sonnet-4-6"
    return resp


async def test_call_claude_returns_text_and_usage(fake_sdk_response, monkeypatch):
    fake_messages = MagicMock()
    fake_messages.create = AsyncMock(return_value=fake_sdk_response)
    fake_client = MagicMock(messages=fake_messages)

    client = ClaudeClient(sdk_client=fake_client)
    result = await client.complete_json(
        system_blocks=[{"type": "text", "text": "SYSTEM"}],
        user_text="USER",
        max_tokens=400,
    )
    assert isinstance(result, ClaudeResponse)
    assert "service" in result.text
    assert result.input_tokens == 120
    assert result.output_tokens == 40
    assert result.cache_read_tokens == 1500


async def test_call_claude_propagates_rate_limit(monkeypatch):
    import anthropic
    fake_messages = MagicMock()
    fake_messages.create = AsyncMock(
        side_effect=anthropic.RateLimitError(
            "rl", response=MagicMock(status_code=429), body=None
        )
    )
    fake_client = MagicMock(messages=fake_messages)

    client = ClaudeClient(sdk_client=fake_client)
    with pytest.raises(anthropic.RateLimitError):
        await client.complete_json(system_blocks=[], user_text="x", max_tokens=10)
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/integrations/test_anthropic_client.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/integrations/anthropic_client.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic

from app.settings import settings

MODEL_PRIMARY = "claude-sonnet-4-6"
MODEL_FALLBACK = "claude-opus-4-7"

# Per-million-token USD prices for cost telemetry.
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0, "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-4-7":   {"input": 15.0, "output": 75.0, "cache_write": 18.75, "cache_read": 1.50},
}


@dataclass
class ClaudeResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    model: str
    cost_usd: float


def compute_cost(model: str, *, input_t: int, output_t: int, cw_t: int, cr_t: int) -> float:
    p = PRICING.get(model, PRICING[MODEL_PRIMARY])
    return (
        input_t * p["input"]
        + output_t * p["output"]
        + cw_t * p["cache_write"]
        + cr_t * p["cache_read"]
    ) / 1_000_000


class ClaudeClient:
    def __init__(self, sdk_client: Any | None = None) -> None:
        self.sdk = sdk_client or AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def complete_json(
        self,
        *,
        system_blocks: list[dict[str, Any]],
        user_text: str,
        max_tokens: int,
        model: str = MODEL_PRIMARY,
        temperature: float = 0.7,
    ) -> ClaudeResponse:
        resp = await self.sdk.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_blocks,
            messages=[{"role": "user", "content": user_text}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content)
        usage = resp.usage
        in_t = getattr(usage, "input_tokens", 0)
        out_t = getattr(usage, "output_tokens", 0)
        cw_t = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cr_t = getattr(usage, "cache_read_input_tokens", 0) or 0
        cost = compute_cost(model, input_t=in_t, output_t=out_t, cw_t=cw_t, cr_t=cr_t)
        return ClaudeResponse(
            text=text,
            input_tokens=in_t,
            output_tokens=out_t,
            cache_write_tokens=cw_t,
            cache_read_tokens=cr_t,
            model=resp.model,
            cost_usd=cost,
        )


claude = ClaudeClient()
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/integrations/test_anthropic_client.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/integrations/anthropic_client.py tests/integrations/test_anthropic_client.py
git commit -m "feat(integrations): async Claude client with cost + cache telemetry"
```

---

### Task 9: Unsplash client

**Files:**
- Create: `app/integrations/unsplash_client.py`
- Create: `tests/integrations/test_unsplash_client.py`

- [ ] **Step 1: Write the failing test**

```python
import httpx
import pytest
import respx

from app.integrations.unsplash_client import UnsplashClient, UnsplashPhoto


@respx.mock
async def test_search_returns_first_photo():
    respx.get("https://api.unsplash.com/search/photos").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {
                    "id": "abc123",
                    "urls": {"raw": "https://r/x", "regular": "https://r/r", "small": "https://r/s"},
                    "user": {"name": "Jane Photographer", "links": {"html": "https://unsplash.com/@jane"}},
                    "links": {"html": "https://unsplash.com/photos/abc123"},
                },
                {"id": "skip"},
            ]
        })
    )
    client = UnsplashClient(http=httpx.AsyncClient())
    photo = await client.search_first("florist arrangement")
    assert isinstance(photo, UnsplashPhoto)
    assert photo.photo_id == "abc123"
    assert "Jane Photographer" in photo.attribution_html


@respx.mock
async def test_search_returns_none_on_empty_results():
    respx.get("https://api.unsplash.com/search/photos").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    client = UnsplashClient(http=httpx.AsyncClient())
    assert await client.search_first("nonsense-query-xyz") is None


@respx.mock
async def test_search_raises_on_5xx():
    respx.get("https://api.unsplash.com/search/photos").mock(
        return_value=httpx.Response(503)
    )
    client = UnsplashClient(http=httpx.AsyncClient())
    with pytest.raises(httpx.HTTPStatusError):
        await client.search_first("any")
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/integrations/test_unsplash_client.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/integrations/unsplash_client.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

import httpx
from loguru import logger

from app.settings import settings

BASE_URL = "https://api.unsplash.com"


@dataclass
class UnsplashPhoto:
    photo_id: str
    url_raw: str
    url_regular: str
    url_small: str
    attribution_html: str
    page_url: str


class UnsplashClient:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self.http = http or httpx.AsyncClient(timeout=10.0)

    async def search_first(self, query: str, *, orientation: str = "landscape") -> UnsplashPhoto | None:
        resp = await self.http.get(
            f"{BASE_URL}/search/photos",
            params={
                "query": query,
                "per_page": 5,
                "orientation": orientation,
                "content_filter": "high",
            },
            headers={
                "Accept-Version": "v1",
                "Authorization": f"Client-ID {settings.unsplash_access_key}",
            },
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            logger.warning("unsplash empty results for query={}", query)
            return None
        r = results[0]
        user = r.get("user") or {}
        user_name = user.get("name", "Unsplash photographer")
        user_link = (user.get("links") or {}).get("html", "https://unsplash.com")
        page_url = (r.get("links") or {}).get("html", "https://unsplash.com")
        return UnsplashPhoto(
            photo_id=r["id"],
            url_raw=r["urls"]["raw"],
            url_regular=r["urls"]["regular"],
            url_small=r["urls"]["small"],
            attribution_html=(
                f'Photo by <a href="{user_link}?utm_source=sitesnap&utm_medium=referral">'
                f'{user_name}</a> on '
                f'<a href="https://unsplash.com/?utm_source=sitesnap&utm_medium=referral">Unsplash</a>'
            ),
            page_url=page_url,
        )

    async def download(self, url: str) -> bytes:
        resp = await self.http.get(url, timeout=20.0)
        resp.raise_for_status()
        return resp.content


unsplash = UnsplashClient()
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/integrations/test_unsplash_client.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/integrations/unsplash_client.py tests/integrations/test_unsplash_client.py
git commit -m "feat(integrations): Unsplash search client with attribution"
```

---

### Task 10: R2 client

**Files:**
- Create: `app/integrations/r2_client.py`
- Create: `tests/integrations/test_r2_client.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.r2_client import R2Client


@pytest.fixture
def fake_s3_ctx():
    s3 = MagicMock()
    s3.put_object = AsyncMock(return_value={"ETag": '"abc"'})
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=s3)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx, s3


async def test_upload_one(fake_s3_ctx):
    ctx, s3 = fake_s3_ctx
    session = MagicMock()
    session.client = MagicMock(return_value=ctx)
    client = R2Client(session=session)

    await client.put(key="sites/x/index.html", body=b"<html></html>",
                     content_type="text/html", cache_control="public, max-age=300")
    s3.put_object.assert_called_once()
    args = s3.put_object.call_args.kwargs
    assert args["Key"] == "sites/x/index.html"
    assert args["ContentType"] == "text/html"
    assert args["CacheControl"] == "public, max-age=300"


async def test_put_many_uploads_in_parallel(fake_s3_ctx):
    ctx, s3 = fake_s3_ctx
    session = MagicMock()
    session.client = MagicMock(return_value=ctx)
    client = R2Client(session=session)

    items = [
        ("sites/x/index.html", b"a", "text/html", "public, max-age=300"),
        ("sites/x/styles.css", b"b", "text/css",  "public, max-age=31536000, immutable"),
    ]
    await client.put_many(items)
    assert s3.put_object.await_count == 2
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/integrations/test_r2_client.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/integrations/r2_client.py`**

```python
from __future__ import annotations

import asyncio
from typing import Any, Iterable

import aioboto3

from app.settings import settings


class R2Client:
    def __init__(self, session: Any | None = None) -> None:
        self.session = session or aioboto3.Session()
        self.endpoint = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"

    def _client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    async def put(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
        cache_control: str,
    ) -> None:
        async with self._client() as s3:
            await s3.put_object(
                Bucket=settings.r2_bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                CacheControl=cache_control,
            )

    async def put_many(self, items: Iterable[tuple[str, bytes, str, str]]) -> None:
        items_list = list(items)
        async with self._client() as s3:
            await asyncio.gather(*[
                s3.put_object(
                    Bucket=settings.r2_bucket,
                    Key=key,
                    Body=body,
                    ContentType=content_type,
                    CacheControl=cache_control,
                )
                for (key, body, content_type, cache_control) in items_list
            ])


r2 = R2Client()
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/integrations/test_r2_client.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/integrations/r2_client.py tests/integrations/test_r2_client.py
git commit -m "feat(integrations): R2 client with parallel upload"
```

---

### Task 11: Resend client

**Files:**
- Create: `app/integrations/resend_client.py`
- Create: `tests/integrations/test_resend_client.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import MagicMock, patch

from app.integrations.resend_client import ResendClient


async def test_send_customer_email_calls_sdk():
    with patch("app.integrations.resend_client.resend.Emails.send", new=MagicMock(return_value={"id": "msg_1"})) as send:
        client = ResendClient()
        msg_id = await client.send(
            to="customer@example.com",
            subject="Your site is live",
            html="<p>hi</p>",
        )
        assert msg_id == "msg_1"
        assert send.call_args.args[0]["to"] == ["customer@example.com"]


async def test_send_operator_email_uses_operator_address():
    with patch("app.integrations.resend_client.resend.Emails.send", new=MagicMock(return_value={"id": "msg_2"})) as send:
        client = ResendClient()
        await client.send_operator(subject="New site", html="<p>done</p>")
        assert send.call_args.args[0]["to"][0].endswith("@sitesnap.app") or \
               send.call_args.args[0]["to"][0] == "ops@sitesnap.app"
```

- [ ] **Step 2: Run test, expect fail**

```bash
uv run pytest tests/integrations/test_resend_client.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/integrations/resend_client.py`**

```python
from __future__ import annotations

import asyncio

import resend

from app.settings import settings

resend.api_key = settings.resend_api_key


class ResendClient:
    async def send(self, *, to: str, subject: str, html: str) -> str:
        # resend SDK is sync; run in thread to keep API async.
        def _send() -> dict:
            return resend.Emails.send(
                {
                    "from": settings.resend_from_email,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                }
            )

        result = await asyncio.to_thread(_send)
        return result.get("id", "")

    async def send_operator(self, *, subject: str, html: str) -> str:
        return await self.send(
            to=settings.resend_operator_email,
            subject=subject,
            html=html,
        )


resend_client = ResendClient()
```

- [ ] **Step 4: Run test, expect pass**

```bash
uv run pytest tests/integrations/test_resend_client.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/integrations/resend_client.py tests/integrations/test_resend_client.py
git commit -m "feat(integrations): Resend client for customer + operator email"
```

---

### Task 12: Unsplash cache table + cache-through

**Files:**
- Create: `migrations/0002_unsplash_cache.sql`
- Modify: `app/integrations/unsplash_client.py`
- Modify: `tests/integrations/test_unsplash_client.py`

- [ ] **Step 1: Write the migration**

```sql
-- 0002_unsplash_cache.sql
create table unsplash_cache (
  query        text primary key,
  photo_id     text not null,
  urls         jsonb not null,
  attribution_html text not null,
  page_url     text not null,
  fetched_at   timestamptz not null default now()
);

create index unsplash_cache_fetched_idx on unsplash_cache(fetched_at);
```

- [ ] **Step 2: Apply migration**

```bash
psql "$SUPABASE_DB_URL" -f migrations/0002_unsplash_cache.sql
```

- [ ] **Step 3: Add `search_cached` test**

Append to `tests/integrations/test_unsplash_client.py`:

```python
from unittest.mock import AsyncMock

async def test_search_cached_hits_db_first_then_falls_through():
    fake_db = AsyncMock()
    fake_db.fetch_cached_photo = AsyncMock(return_value=None)
    fake_db.store_cached_photo = AsyncMock()

    client = UnsplashClient(http=httpx.AsyncClient())
    # monkeypatch search_first to a known result
    async def fake_search(_q, **_kw):
        return UnsplashPhoto(
            photo_id="cached1", url_raw="r", url_regular="reg", url_small="s",
            attribution_html="attr", page_url="p",
        )
    client.search_first = fake_search  # type: ignore[assignment]

    photo = await client.search_cached("test-q", db=fake_db, ttl_days=90)
    assert photo and photo.photo_id == "cached1"
    fake_db.store_cached_photo.assert_awaited_once()
```

- [ ] **Step 4: Extend `app/integrations/unsplash_client.py`**

Add at top of file:

```python
import json
from datetime import datetime, timedelta, timezone
```

Add methods to `UnsplashClient`:

```python
    async def search_cached(
        self,
        query: str,
        *,
        db: "CacheStore",
        ttl_days: int = 90,
        orientation: str = "landscape",
    ) -> UnsplashPhoto | None:
        cached = await db.fetch_cached_photo(query)
        if cached and cached["fetched_at"] > datetime.now(timezone.utc) - timedelta(days=ttl_days):
            urls = cached["urls"]
            return UnsplashPhoto(
                photo_id=cached["photo_id"],
                url_raw=urls["raw"],
                url_regular=urls["regular"],
                url_small=urls["small"],
                attribution_html=cached["attribution_html"],
                page_url=cached["page_url"],
            )

        photo = await self.search_first(query, orientation=orientation)
        if photo is not None:
            await db.store_cached_photo(
                query=query,
                photo_id=photo.photo_id,
                urls={"raw": photo.url_raw, "regular": photo.url_regular, "small": photo.url_small},
                attribution_html=photo.attribution_html,
                page_url=photo.page_url,
            )
        return photo
```

Add a Protocol at module top:

```python
from typing import Protocol


class CacheStore(Protocol):
    async def fetch_cached_photo(self, query: str) -> dict | None: ...
    async def store_cached_photo(
        self, *, query: str, photo_id: str, urls: dict, attribution_html: str, page_url: str
    ) -> None: ...
```

- [ ] **Step 5: Add corresponding DB methods to `app/db.py`**

Append to `DB` class:

```python
    async def fetch_cached_photo(self, query: str) -> dict | None:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            "select photo_id, urls, attribution_html, page_url, fetched_at from unsplash_cache where query = $1",
            query,
        )
        if not row:
            return None
        return {
            "photo_id": row["photo_id"],
            "urls": json.loads(row["urls"]) if isinstance(row["urls"], str) else row["urls"],
            "attribution_html": row["attribution_html"],
            "page_url": row["page_url"],
            "fetched_at": row["fetched_at"],
        }

    async def store_cached_photo(
        self, *, query: str, photo_id: str, urls: dict, attribution_html: str, page_url: str
    ) -> None:
        assert self.pool is not None
        await self.pool.execute(
            """
            insert into unsplash_cache (query, photo_id, urls, attribution_html, page_url)
            values ($1, $2, $3::jsonb, $4, $5)
            on conflict (query) do update set
              photo_id = excluded.photo_id,
              urls = excluded.urls,
              attribution_html = excluded.attribution_html,
              page_url = excluded.page_url,
              fetched_at = now()
            """,
            query, photo_id, json.dumps(urls), attribution_html, page_url,
        )
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/integrations/test_unsplash_client.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add migrations/0002_unsplash_cache.sql app/integrations/unsplash_client.py app/db.py tests/integrations/test_unsplash_client.py
git commit -m "feat(integrations): unsplash cache-through with 90-day TTL"
```

---

## Phase 4 — Prompts and templates

### Task 13: System classifier prompt

**Files:**
- Create: `prompts/system_classifier.md`

- [ ] **Step 1: Write the prompt**

```markdown
You are an expert brand classifier for a website builder called SiteSnap. Given a brand's basic information, you assign it to one of three website archetypes that we have pre-designed.

## The three archetypes

**service** — Professional service businesses where trust, expertise, and consultation matter. Examples: dental clinics, accounting firms, law practices, salons, fitness coaches, contractors, marketing agencies, IT consultancies. The home page sells *what you do for the customer* and *why to trust you*.

**hospitality** — Businesses where atmosphere, food, drink, or stay is the product. Examples: restaurants, cafes, bars, hotels, B&Bs, event venues, bakeries, food trucks. The home page sells *the sensory experience* and *the menu/offering*.

**portfolio** — Creative practitioners and studios where the work itself is the pitch. Examples: photographers, designers, illustrators, architects, artisans, makers, individual creatives, boutique studios. The home page sells *the body of work*.

## Decision rules

- If unsure between `service` and `portfolio`, prefer `service` unless the brand's primary output is a portfolio of creative pieces.
- If the brand sells food, drink, or accommodation as its core product, always `hospitality`.
- Confidence < 0.6 will be overridden by the orchestrator to `service`. Be honest about uncertainty.

## Output format

Respond with a single JSON object and nothing else:

```json
{"archetype": "service" | "hospitality" | "portfolio", "confidence": 0.0..1.0, "reasoning": "one short sentence"}
```
```

- [ ] **Step 2: Commit**

```bash
git add prompts/system_classifier.md
git commit -m "feat(prompts): system prompt for archetype classifier"
```

---

### Task 14: System copywriter prompt

**Files:**
- Create: `prompts/system_copywriter.md`

- [ ] **Step 1: Write the prompt**

```markdown
You are a senior brand copywriter and editor for SiteSnap, a website builder. Given a brand's information and a chosen archetype, you write the complete copy for a single-page website.

## Voice principles

- **Specific over vague.** "Cuts every morning at 6am" beats "fresh daily."
- **Plain over corporate.** "We answer in an hour" beats "rapid response times."
- **Active over passive.** "We build" beats "is built by us."
- **No invented facts.** Don't fabricate awards, founding years, or named customers. `social_proof` quotes should sound *plausible and generic* (first name + last initial), never a real-looking attribution.
- **No emojis** in any field.
- **No clichés.** Avoid "elevate," "unlock," "synergy," "best-in-class," "passion-driven."

## Length budgets

- `headline`: 4–9 words
- `subheadline`: 12–22 words
- `primary_cta`, `secondary_cta`: 2–4 words
- `about.heading`: 2–5 words
- `about.body`: 40–80 words
- `features[].title`: 2–4 words
- `features[].body`: 12–22 words
- `social_proof[].text`: 8–20 words
- `footer_tagline`: 4–10 words
- `meta.title`: ≤60 chars
- `meta.description`: 120–160 chars

## Palette hints

Pick one `palette_hint` that fits the brand's mood:

- `warm-earth` — natural, grounded, hand-made, hospitable (florists, bakeries, woodworking, traditional services)
- `cool-modern` — clean, professional, tech-aware, calm (SaaS, clinics, consultancies, modern restaurants)
- `bold-vibrant` — energetic, youthful, attention-grabbing (fitness, agencies, creative studios, food trucks)
- `muted-elegant` — refined, premium, considered, quiet luxury (boutique services, fine dining, high-end portfolios)

## Output format

Return a single JSON object matching the schema below exactly. No prose before or after.

```json
{
  "headline": "string",
  "subheadline": "string",
  "primary_cta": "string",
  "secondary_cta": "string",
  "about": {"heading": "string", "body": "string"},
  "features": [
    {"icon": "string", "title": "string", "body": "string"},
    {"icon": "string", "title": "string", "body": "string"},
    {"icon": "string", "title": "string", "body": "string"}
  ],
  "social_proof": [
    {"text": "string", "author": "First L."}
  ],
  "footer_tagline": "string",
  "meta": {"title": "string", "description": "string", "keywords": ["string"]},
  "palette_hint": "warm-earth" | "cool-modern" | "bold-vibrant" | "muted-elegant"
}
```

The `icon` field is a single lowercase keyword (e.g. `leaf`, `clock`, `shield`, `heart`, `star`, `phone`, `map`, `mail`, `camera`, `coffee`). The renderer maps it to an inline SVG.
```

- [ ] **Step 2: Commit**

```bash
git add prompts/system_copywriter.md
git commit -m "feat(prompts): system prompt for copywriter with voice + budget rules"
```

---

### Task 15: Three archetype prompts

**Files:**
- Create: `prompts/archetype_service.md`
- Create: `prompts/archetype_hospitality.md`
- Create: `prompts/archetype_portfolio.md`

- [ ] **Step 1: Write `prompts/archetype_service.md`**

```markdown
## Archetype: service

You are writing for a professional service business. Center the customer's outcome and the trust signals that justify hiring this brand.

- `headline` should name the *outcome* the customer wants, not the brand's process.
- `subheadline` should specify *for whom* and *the differentiator* in one breath.
- `features` should be three concrete things the customer experiences when working with this business — not vague benefits. Use icons like `clock`, `shield`, `phone`, `check`, `chat`, `map`, `award`.
- `about.heading` is the brand's positioning statement (3–5 words), not the word "About."
- `about.body` answers: who founded this, why, how the team is qualified — without inventing facts. If you don't know, write about the principles the brand operates by.
- `primary_cta` is a low-friction next step: "Book a call", "Request a quote", "See pricing", "Get started".
- `secondary_cta` is the soft option: "See our work", "Read more", "About us".
- `social_proof` should be 1–2 generic testimonials (first name + last initial).
```

- [ ] **Step 2: Write `prompts/archetype_hospitality.md`**

```markdown
## Archetype: hospitality

You are writing for a food, drink, or stay business. Center the sensory experience and what's on offer right now.

- `headline` evokes a sensation, place, or moment — not a feature list.
- `subheadline` says where (city / neighborhood) and what genre/offering.
- `features` should describe the experience: ambience, signature offering, hours/availability. Use icons like `coffee`, `flame`, `leaf`, `clock`, `map`, `star`, `wine`, `bed`.
- `about.heading` is the brand's identity in 3–5 words (e.g. "Wood-fired since 2014").
- `about.body` describes the kitchen / room / craft — what's distinctive about the ingredients, technique, or atmosphere.
- `primary_cta` is the action a hungry person takes: "Reserve a table", "Order online", "See menu", "Book a stay".
- `secondary_cta`: "View gallery", "Find us", "Today's hours".
- `social_proof` quotes should sound like a real customer remembering one specific thing they liked.
```

- [ ] **Step 3: Write `prompts/archetype_portfolio.md`**

```markdown
## Archetype: portfolio

You are writing for a creative practitioner or studio. Let the work speak; copy is restrained, confident, specific.

- `headline` is short and assertive (4–6 words). The practitioner's name or a one-line positioning. Avoid adjectives.
- `subheadline` names the *medium* and *the kind of clients/work* in plain language.
- `features` describe how the practitioner works: process, materials, format, availability. Use icons like `camera`, `pencil`, `compass`, `palette`, `monitor`, `book`, `globe`.
- `about.heading` is a positioning fragment (e.g. "Independent since 2018").
- `about.body` describes the practitioner's approach, background, and the kind of work they take on — without bravado.
- `primary_cta`: "View work", "See projects", "Get in touch".
- `secondary_cta`: "About me", "Process", "CV".
- `social_proof` should sound like a past client/collaborator describing the working relationship, not the deliverable.
```

- [ ] **Step 4: Commit**

```bash
git add prompts/archetype_service.md prompts/archetype_hospitality.md prompts/archetype_portfolio.md
git commit -m "feat(prompts): per-archetype copywriting guidance"
```

---

### Task 16: Service archetype template

**Files:**
- Create: `templates/service/index.html.j2`
- Create: `templates/service/manifest.json`

- [ ] **Step 1: Write `templates/service/manifest.json`**

```json
{
  "archetype": "service",
  "image_slots": {
    "hero":      { "query_template": "{industry} professional",       "orientation": "landscape" },
    "feature_1": { "query_template": "{industry} workspace minimal",  "orientation": "squarish"  },
    "feature_2": { "query_template": "{industry} team meeting calm",  "orientation": "squarish"  },
    "feature_3": { "query_template": "{industry} customer happy",     "orientation": "squarish"  }
  }
}
```

- [ ] **Step 2: Write `templates/service/index.html.j2`**

```jinja2
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ copy.meta.title }}</title>
<meta name="description" content="{{ copy.meta.description }}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:wght@500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --primary: {{ palette.primary }};
    --accent: {{ palette.accent }};
    --bg: {{ palette.neutral_bg }};
    --surface: {{ palette.neutral_surface }};
    --ink: {{ palette.ink }};
    --ink-soft: {{ palette.ink_soft }};
    --serif: 'Fraunces', Georgia, serif;
    --sans: 'Inter', -apple-system, system-ui, sans-serif;
  }
  *,*::before,*::after { box-sizing: border-box; }
  html,body { margin: 0; padding: 0; }
  body { font-family: var(--sans); background: var(--bg); color: var(--ink); line-height: 1.55; -webkit-font-smoothing: antialiased; }
  a { color: var(--primary); text-decoration: none; }
  .wrap { max-width: 1120px; margin: 0 auto; padding: 0 24px; }
  header { padding: 24px 0; }
  .nav { display: flex; align-items: center; justify-content: space-between; }
  .brand { font-family: var(--serif); font-weight: 700; font-size: 22px; color: var(--ink); }
  .btn { display: inline-block; padding: 14px 22px; border-radius: 999px; font-weight: 600; font-size: 15px; transition: transform .15s; }
  .btn:hover { transform: translateY(-1px); }
  .btn-primary { background: var(--primary); color: var(--surface); }
  .btn-ghost { background: transparent; color: var(--ink); border: 1px solid color-mix(in srgb, var(--ink) 15%, transparent); }
  .hero { padding: 64px 0 96px; display: grid; grid-template-columns: 1.1fr .9fr; gap: 56px; align-items: center; }
  .hero h1 { font-family: var(--serif); font-size: clamp(40px, 6vw, 64px); line-height: 1.05; margin: 0 0 20px; letter-spacing: -.02em; }
  .hero p.lede { font-size: 19px; color: var(--ink-soft); margin: 0 0 32px; max-width: 30em; }
  .hero-actions { display: flex; gap: 12px; flex-wrap: wrap; }
  .hero-image { aspect-ratio: 4/5; border-radius: 24px; overflow: hidden; background: var(--surface); box-shadow: 0 40px 60px -30px color-mix(in srgb, var(--ink) 30%, transparent); }
  .hero-image img { width: 100%; height: 100%; object-fit: cover; display: block; }
  section { padding: 64px 0; }
  h2 { font-family: var(--serif); font-size: clamp(28px, 4vw, 42px); margin: 0 0 12px; letter-spacing: -.015em; }
  .section-lede { color: var(--ink-soft); max-width: 36em; margin: 0 0 40px; font-size: 17px; }
  .features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
  .feature { background: var(--surface); border-radius: 20px; padding: 28px; }
  .feature .icon { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; background: color-mix(in srgb, var(--accent) 25%, transparent); color: var(--primary); margin-bottom: 18px; }
  .feature h3 { margin: 0 0 8px; font-size: 18px; }
  .feature p { margin: 0; color: var(--ink-soft); font-size: 15px; }
  .about { display: grid; grid-template-columns: 1fr 1fr; gap: 56px; align-items: center; }
  .about-photos { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .about-photos img { width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 16px; display: block; }
  .quotes { background: var(--surface); border-radius: 24px; padding: 56px; text-align: center; }
  .quotes blockquote { font-family: var(--serif); font-size: clamp(22px, 3vw, 30px); line-height: 1.3; margin: 0 auto 16px; max-width: 28em; }
  .quotes cite { color: var(--ink-soft); font-style: normal; font-size: 15px; }
  .cta { background: var(--ink); color: var(--surface); border-radius: 28px; padding: 72px 32px; text-align: center; }
  .cta h2 { color: var(--surface); }
  .cta .btn-primary { background: var(--accent); color: var(--ink); }
  footer { padding: 48px 0; color: var(--ink-soft); font-size: 14px; text-align: center; }
  footer .attribution { margin-top: 12px; font-size: 12px; opacity: .7; }
  footer .attribution a { color: var(--ink-soft); }
  @media (max-width: 800px) {
    .hero, .about { grid-template-columns: 1fr; }
    .features { grid-template-columns: 1fr; }
    .quotes, .cta { padding: 40px 24px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header><nav class="nav">
    <div class="brand">{{ brand.name }}</div>
    <a class="btn btn-ghost" href="#contact">{{ copy.secondary_cta }}</a>
  </nav></header>

  <section class="hero">
    <div>
      <h1>{{ copy.headline }}</h1>
      <p class="lede">{{ copy.subheadline }}</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="#contact">{{ copy.primary_cta }}</a>
        <a class="btn btn-ghost" href="#about">{{ copy.secondary_cta }}</a>
      </div>
    </div>
    <div class="hero-image"><img src="{{ images.hero.local }}" alt="{{ brand.name }}"></div>
  </section>

  <section>
    <h2>{{ copy.about.heading }}</h2>
    <p class="section-lede">{{ copy.about.body }}</p>
    <div class="features">
      {% for f in copy.features %}
      <div class="feature">
        <div class="icon">{% include 'icons/' ~ (f.icon | default('star')) ~ '.svg' ignore missing %}</div>
        <h3>{{ f.title }}</h3>
        <p>{{ f.body }}</p>
      </div>
      {% endfor %}
    </div>
  </section>

  {% if copy.social_proof %}
  <section>
    <div class="quotes">
      <blockquote>&ldquo;{{ copy.social_proof[0].text }}&rdquo;</blockquote>
      <cite>— {{ copy.social_proof[0].author }}</cite>
    </div>
  </section>
  {% endif %}

  <section id="contact">
    <div class="cta">
      <h2>{{ copy.footer_tagline }}</h2>
      <a class="btn btn-primary" href="mailto:hello@{{ brand.slug }}.sitesnap.app">{{ copy.primary_cta }}</a>
    </div>
  </section>

  <footer>
    <div>&copy; {{ now.year }} {{ brand.name }}</div>
    <div class="attribution">{{ images.hero.attribution | safe }}</div>
  </footer>
</div>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add templates/service
git commit -m "feat(templates): service archetype (single page, inline CSS)"
```

---

### Task 17: Hospitality archetype template

**Files:**
- Create: `templates/hospitality/index.html.j2`
- Create: `templates/hospitality/manifest.json`

- [ ] **Step 1: Write `templates/hospitality/manifest.json`**

```json
{
  "archetype": "hospitality",
  "image_slots": {
    "hero":      { "query_template": "{industry} food atmospheric",  "orientation": "landscape" },
    "feature_1": { "query_template": "{industry} ingredient close",  "orientation": "squarish"  },
    "feature_2": { "query_template": "{industry} interior warm",     "orientation": "squarish"  },
    "feature_3": { "query_template": "{industry} dish overhead",     "orientation": "squarish"  }
  }
}
```

- [ ] **Step 2: Write `templates/hospitality/index.html.j2`**

```jinja2
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ copy.meta.title }}</title>
<meta name="description" content="{{ copy.meta.description }}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --primary: {{ palette.primary }};
    --accent: {{ palette.accent }};
    --bg: {{ palette.neutral_bg }};
    --surface: {{ palette.neutral_surface }};
    --ink: {{ palette.ink }};
    --ink-soft: {{ palette.ink_soft }};
    --display: 'Playfair Display', Georgia, serif;
    --body: 'Inter', system-ui, sans-serif;
  }
  *,*::before,*::after { box-sizing: border-box; }
  html,body { margin: 0; padding: 0; }
  body { font-family: var(--body); background: var(--bg); color: var(--ink); line-height: 1.55; }
  a { color: var(--primary); text-decoration: none; }
  .wrap { max-width: 1180px; margin: 0 auto; padding: 0 24px; }
  .hero { position: relative; min-height: 88vh; display: grid; place-items: center; color: #fff; text-align: center; overflow: hidden; border-radius: 0 0 32px 32px; }
  .hero::before { content: ''; position: absolute; inset: 0; background-image: url('{{ images.hero.local }}'); background-size: cover; background-position: center; z-index: 0; }
  .hero::after { content: ''; position: absolute; inset: 0; background: linear-gradient(180deg, color-mix(in srgb, var(--ink) 35%, transparent) 0%, color-mix(in srgb, var(--ink) 70%, transparent) 100%); z-index: 1; }
  .hero-inner { position: relative; z-index: 2; padding: 96px 24px; max-width: 760px; }
  .hero h1 { font-family: var(--display); font-size: clamp(44px, 7vw, 76px); line-height: 1.05; margin: 0 0 20px; font-weight: 700; }
  .hero p.lede { font-size: 19px; opacity: .9; margin: 0 0 32px; }
  .btn { display: inline-block; padding: 16px 28px; border-radius: 999px; font-weight: 600; transition: transform .15s; }
  .btn:hover { transform: translateY(-1px); }
  .btn-primary { background: var(--accent); color: var(--ink); }
  .btn-ghost-light { color: #fff; border: 1px solid rgba(255,255,255,.5); }
  .nav { position: absolute; top: 0; left: 0; right: 0; z-index: 3; display: flex; align-items: center; justify-content: space-between; padding: 24px 32px; }
  .brand { font-family: var(--display); font-size: 22px; font-weight: 700; color: #fff; }
  section.story { padding: 96px 0; text-align: center; }
  h2 { font-family: var(--display); font-size: clamp(32px, 5vw, 52px); margin: 0 0 16px; }
  .story p.lede { color: var(--ink-soft); max-width: 38em; margin: 0 auto 56px; font-size: 18px; }
  .gallery { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .gallery figure { margin: 0; aspect-ratio: 1/1; overflow: hidden; border-radius: 16px; }
  .gallery img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .4s; }
  .gallery figure:hover img { transform: scale(1.04); }
  .feature-strip { background: var(--primary); color: var(--surface); padding: 64px 0; }
  .feature-strip .features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
  .feature { padding: 0 8px; }
  .feature h3 { font-family: var(--display); font-size: 22px; margin: 0 0 8px; }
  .feature p { margin: 0; opacity: .85; font-size: 15px; }
  .quotes { padding: 96px 0; text-align: center; }
  .quotes blockquote { font-family: var(--display); font-size: clamp(22px, 3vw, 32px); line-height: 1.35; margin: 0 auto 16px; max-width: 32em; font-style: italic; }
  .quotes cite { color: var(--ink-soft); font-style: normal; }
  .cta { padding: 96px 0; text-align: center; background: var(--ink); color: var(--surface); }
  .cta h2 { color: var(--surface); }
  footer { padding: 48px 0; text-align: center; color: var(--ink-soft); font-size: 14px; }
  footer .attribution { margin-top: 12px; font-size: 12px; opacity: .7; }
  footer .attribution a { color: var(--ink-soft); }
  @media (max-width: 800px) {
    .gallery, .feature-strip .features { grid-template-columns: 1fr; }
    .nav { padding: 18px 20px; }
  }
</style>
</head>
<body>
<header class="hero">
  <nav class="nav">
    <div class="brand">{{ brand.name }}</div>
    <a class="btn btn-ghost-light" href="#visit">{{ copy.secondary_cta }}</a>
  </nav>
  <div class="hero-inner">
    <h1>{{ copy.headline }}</h1>
    <p class="lede">{{ copy.subheadline }}</p>
    <a class="btn btn-primary" href="#visit">{{ copy.primary_cta }}</a>
  </div>
</header>

<section class="story">
  <div class="wrap">
    <h2>{{ copy.about.heading }}</h2>
    <p class="lede">{{ copy.about.body }}</p>
    <div class="gallery">
      <figure><img src="{{ images.feature_1.local }}" alt=""></figure>
      <figure><img src="{{ images.feature_2.local }}" alt=""></figure>
      <figure><img src="{{ images.feature_3.local }}" alt=""></figure>
    </div>
  </div>
</section>

<section class="feature-strip">
  <div class="wrap">
    <div class="features">
      {% for f in copy.features %}
      <div class="feature"><h3>{{ f.title }}</h3><p>{{ f.body }}</p></div>
      {% endfor %}
    </div>
  </div>
</section>

{% if copy.social_proof %}
<section class="quotes">
  <div class="wrap">
    <blockquote>&ldquo;{{ copy.social_proof[0].text }}&rdquo;</blockquote>
    <cite>— {{ copy.social_proof[0].author }}</cite>
  </div>
</section>
{% endif %}

<section id="visit" class="cta">
  <div class="wrap">
    <h2>{{ copy.footer_tagline }}</h2>
    <p style="opacity:.85; margin-bottom:32px;">{{ copy.about.heading }}</p>
    <a class="btn btn-primary" href="mailto:hello@{{ brand.slug }}.sitesnap.app">{{ copy.primary_cta }}</a>
  </div>
</section>

<footer>
  <div>&copy; {{ now.year }} {{ brand.name }}</div>
  <div class="attribution">{{ images.hero.attribution | safe }}</div>
</footer>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add templates/hospitality
git commit -m "feat(templates): hospitality archetype (full-bleed hero, gallery)"
```

---

### Task 18: Portfolio archetype template

**Files:**
- Create: `templates/portfolio/index.html.j2`
- Create: `templates/portfolio/manifest.json`

- [ ] **Step 1: Write `templates/portfolio/manifest.json`**

```json
{
  "archetype": "portfolio",
  "image_slots": {
    "hero":      { "query_template": "{industry} work showcase",     "orientation": "landscape" },
    "feature_1": { "query_template": "{industry} project minimal",   "orientation": "squarish"  },
    "feature_2": { "query_template": "{industry} detail texture",    "orientation": "squarish"  },
    "feature_3": { "query_template": "{industry} workspace",         "orientation": "squarish"  }
  }
}
```

- [ ] **Step 2: Write `templates/portfolio/index.html.j2`**

```jinja2
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ copy.meta.title }}</title>
<meta name="description" content="{{ copy.meta.description }}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --primary: {{ palette.primary }};
    --accent: {{ palette.accent }};
    --bg: {{ palette.neutral_bg }};
    --surface: {{ palette.neutral_surface }};
    --ink: {{ palette.ink }};
    --ink-soft: {{ palette.ink_soft }};
    --display: 'Space Grotesk', system-ui, sans-serif;
    --body: 'Inter', system-ui, sans-serif;
  }
  *,*::before,*::after { box-sizing: border-box; }
  html,body { margin: 0; padding: 0; }
  body { font-family: var(--body); background: var(--bg); color: var(--ink); line-height: 1.55; }
  a { color: var(--primary); text-decoration: none; }
  .wrap { max-width: 1200px; margin: 0 auto; padding: 0 32px; }
  header { padding: 32px 0; }
  .nav { display: flex; align-items: center; justify-content: space-between; }
  .brand { font-family: var(--display); font-weight: 700; font-size: 20px; letter-spacing: -.01em; }
  .nav .links a { margin-left: 24px; color: var(--ink-soft); font-size: 14px; font-weight: 500; }
  .hero { padding: 96px 0 64px; }
  .hero h1 { font-family: var(--display); font-size: clamp(56px, 10vw, 120px); line-height: .95; margin: 0 0 24px; letter-spacing: -.03em; font-weight: 700; }
  .hero p.lede { font-size: 21px; color: var(--ink-soft); margin: 0 0 32px; max-width: 28em; }
  .hero-actions { display: flex; gap: 16px; flex-wrap: wrap; }
  .btn { display: inline-block; padding: 14px 24px; border-radius: 8px; font-weight: 500; font-size: 15px; transition: transform .15s; }
  .btn:hover { transform: translateY(-1px); }
  .btn-primary { background: var(--ink); color: var(--bg); }
  .btn-ghost { color: var(--ink); border: 1px solid color-mix(in srgb, var(--ink) 20%, transparent); }
  section { padding: 80px 0; }
  .work-grid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 32px; }
  .work-grid figure { margin: 0; border-radius: 12px; overflow: hidden; }
  .work-grid img { width: 100%; height: 100%; object-fit: cover; display: block; aspect-ratio: 4/3; }
  .work-grid .stack { display: grid; grid-template-rows: 1fr 1fr; gap: 32px; }
  h2 { font-family: var(--display); font-size: clamp(28px, 4vw, 44px); margin: 0 0 12px; letter-spacing: -.02em; }
  .lede { color: var(--ink-soft); max-width: 36em; font-size: 17px; }
  .principles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 48px; margin-top: 56px; }
  .principle .num { font-family: var(--display); font-size: 13px; color: var(--accent); font-weight: 700; letter-spacing: .12em; }
  .principle h3 { font-family: var(--display); font-size: 22px; margin: 8px 0; letter-spacing: -.01em; }
  .principle p { margin: 0; color: var(--ink-soft); font-size: 15px; }
  .quotes { border-top: 1px solid color-mix(in srgb, var(--ink) 12%, transparent); border-bottom: 1px solid color-mix(in srgb, var(--ink) 12%, transparent); padding: 64px 0; text-align: center; }
  .quotes blockquote { font-family: var(--display); font-size: clamp(22px, 3vw, 32px); line-height: 1.35; margin: 0 auto 16px; max-width: 30em; font-weight: 500; letter-spacing: -.01em; }
  .quotes cite { color: var(--ink-soft); font-style: normal; }
  .cta { text-align: left; }
  .cta h2 { max-width: 14em; }
  footer { padding: 48px 0; color: var(--ink-soft); font-size: 13px; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 16px; }
  footer .attribution { font-size: 12px; opacity: .7; }
  footer .attribution a { color: var(--ink-soft); }
  @media (max-width: 800px) {
    .work-grid, .principles { grid-template-columns: 1fr; }
    .work-grid .stack { grid-template-rows: auto auto; }
    .nav .links a { margin-left: 16px; }
  }
</style>
</head>
<body>
<div class="wrap">
  <header><nav class="nav">
    <div class="brand">{{ brand.name }}</div>
    <div class="links">
      <a href="#work">Work</a>
      <a href="#about">About</a>
      <a href="#contact">Contact</a>
    </div>
  </nav></header>

  <section class="hero">
    <h1>{{ copy.headline }}</h1>
    <p class="lede">{{ copy.subheadline }}</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="#work">{{ copy.primary_cta }}</a>
      <a class="btn btn-ghost" href="#about">{{ copy.secondary_cta }}</a>
    </div>
  </section>

  <section id="work">
    <div class="work-grid">
      <figure><img src="{{ images.hero.local }}" alt=""></figure>
      <div class="stack">
        <figure><img src="{{ images.feature_1.local }}" alt=""></figure>
        <figure><img src="{{ images.feature_2.local }}" alt=""></figure>
      </div>
    </div>
  </section>

  <section id="about">
    <h2>{{ copy.about.heading }}</h2>
    <p class="lede">{{ copy.about.body }}</p>
    <div class="principles">
      {% for f in copy.features %}
      <div class="principle">
        <div class="num">0{{ loop.index }}</div>
        <h3>{{ f.title }}</h3>
        <p>{{ f.body }}</p>
      </div>
      {% endfor %}
    </div>
  </section>

  {% if copy.social_proof %}
  <section class="quotes">
    <blockquote>&ldquo;{{ copy.social_proof[0].text }}&rdquo;</blockquote>
    <cite>— {{ copy.social_proof[0].author }}</cite>
  </section>
  {% endif %}

  <section id="contact" class="cta">
    <h2>{{ copy.footer_tagline }}</h2>
    <a class="btn btn-primary" href="mailto:hello@{{ brand.slug }}.sitesnap.app">{{ copy.primary_cta }}</a>
  </section>

  <footer>
    <div>&copy; {{ now.year }} {{ brand.name }}</div>
    <div class="attribution">{{ images.hero.attribution | safe }}</div>
  </footer>
</div>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add templates/portfolio
git commit -m "feat(templates): portfolio archetype (type-driven, work grid)"
```

---

### Task 19: Status page template

**Files:**
- Create: `templates/status.html.j2`

- [ ] **Step 1: Write the template**

```jinja2
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Building your site...</title>
<style>
  :root { --bg: #0B0B0F; --surface: #15151B; --primary: #38BDF8; --ink: #F8FAFC; --ink-soft: #94A3B8; }
  *,*::before,*::after { box-sizing: border-box; }
  html,body { margin: 0; padding: 0; height: 100%; }
  body { font-family: -apple-system, system-ui, 'Segoe UI', sans-serif; background: var(--bg); color: var(--ink); display: grid; place-items: center; min-height: 100dvh; line-height: 1.5; }
  .card { background: var(--surface); border-radius: 24px; padding: 56px 48px; max-width: 540px; width: calc(100% - 32px); text-align: center; box-shadow: 0 60px 80px -40px rgba(0,0,0,.6); }
  h1 { margin: 0 0 8px; font-size: 28px; font-weight: 700; letter-spacing: -.01em; }
  p { margin: 0 0 32px; color: var(--ink-soft); font-size: 15px; }
  .progress { height: 8px; border-radius: 999px; background: rgba(255,255,255,.08); overflow: hidden; margin-bottom: 18px; }
  .bar { height: 100%; width: 0%; background: linear-gradient(90deg, var(--primary), #818CF8); transition: width .6s cubic-bezier(.2,.8,.2,1); }
  .stage { font-size: 13px; color: var(--ink-soft); margin-bottom: 24px; letter-spacing: .04em; text-transform: uppercase; }
  .live { display: none; padding: 20px; border: 1px solid rgba(56,189,248,.3); border-radius: 16px; }
  .live.show { display: block; }
  .live h2 { margin: 0 0 8px; font-size: 20px; }
  .live a { color: var(--primary); font-weight: 600; word-break: break-all; }
  .error { display: none; padding: 20px; border: 1px solid rgba(239,68,68,.3); border-radius: 16px; color: #FCA5A5; }
  .error.show { display: block; }
</style>
</head>
<body>
<main class="card">
  <h1>Building your site</h1>
  <p>This usually takes 20–40 seconds. Stay on this page — we'll show your live URL the moment it's ready.</p>
  <div class="progress"><div class="bar" id="bar"></div></div>
  <div class="stage" id="stage">Preparing…</div>
  <div class="live" id="live">
    <h2>Your site is live</h2>
    <a id="liveurl" href="#" target="_blank" rel="noopener">…</a>
  </div>
  <div class="error" id="error"></div>
</main>
<script>
  const jobId = "{{ job_id }}";
  const STAGE_LABEL = {
    queued: "Queued…",
    classifying: "Picking a layout…",
    writing_copy: "Writing your copy…",
    fetching_images: "Choosing photography…",
    rendering: "Designing the page…",
    publishing: "Publishing to the web…",
    notifying: "Sending you the link…",
    done: "Done!",
    failed: "Something went wrong",
  };
  async function tick() {
    try {
      const r = await fetch(`/api/jobs/${jobId}`, { cache: "no-store" });
      if (!r.ok) throw new Error("status " + r.status);
      const j = await r.json();
      document.getElementById("bar").style.width = (j.progress_pct || 0) + "%";
      document.getElementById("stage").textContent = STAGE_LABEL[j.status] || j.status;
      if (j.status === "done" && j.site_url) {
        const live = document.getElementById("live");
        live.classList.add("show");
        const a = document.getElementById("liveurl");
        a.href = j.site_url; a.textContent = j.site_url;
        return;
      }
      if (j.status === "failed") {
        const e = document.getElementById("error");
        e.classList.add("show");
        e.textContent = (j.error && j.error.message) || "Generation failed. We've been notified.";
        return;
      }
    } catch (err) { /* network blip; just keep going */ }
    setTimeout(tick, 2000);
  }
  tick();
</script>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/status.html.j2
git commit -m "feat(templates): status page with 2s polling and progress bar"
```

---

## Phase 5 — Pipeline stages

### Task 20: Stage 1 — `classify`

**Files:**
- Create: `app/pipeline/classify.py`
- Create: `tests/pipeline/__init__.py`, `tests/pipeline/test_classify.py`

- [ ] **Step 1: Write the failing test**

`tests/pipeline/__init__.py` is empty. `tests/pipeline/test_classify.py`:

```python
from unittest.mock import AsyncMock

import pytest

from app.integrations.anthropic_client import ClaudeResponse
from app.pipeline.classify import classify_submission


@pytest.fixture
def fake_claude():
    client = AsyncMock()
    client.complete_json = AsyncMock(return_value=ClaudeResponse(
        text='{"archetype":"hospitality","confidence":0.92,"reasoning":"r"}',
        input_tokens=100, output_tokens=20, cache_write_tokens=0, cache_read_tokens=1200,
        model="claude-sonnet-4-6", cost_usd=0.001,
    ))
    return client


async def test_classify_returns_parsed_output(fake_claude):
    out = await classify_submission(
        claude=fake_claude,
        industry="bakery", brand_name="Loaf", questionnaire={"tone": "warm"},
    )
    assert out.archetype == "hospitality"
    assert out.confidence == pytest.approx(0.92)


async def test_classify_falls_back_when_low_confidence():
    client = AsyncMock()
    client.complete_json = AsyncMock(return_value=ClaudeResponse(
        text='{"archetype":"portfolio","confidence":0.4,"reasoning":"r"}',
        input_tokens=100, output_tokens=20, cache_write_tokens=0, cache_read_tokens=1200,
        model="claude-sonnet-4-6", cost_usd=0.001,
    ))
    out = await classify_submission(
        claude=client, industry="x", brand_name="y", questionnaire={},
    )
    assert out.archetype == "service"  # forced fallback


async def test_classify_handles_garbage_json_via_retry():
    bad = ClaudeResponse(
        text="not json", input_tokens=10, output_tokens=2,
        cache_write_tokens=0, cache_read_tokens=0, model="claude-sonnet-4-6", cost_usd=0,
    )
    good = ClaudeResponse(
        text='{"archetype":"service","confidence":0.7,"reasoning":""}',
        input_tokens=10, output_tokens=10, cache_write_tokens=0, cache_read_tokens=0,
        model="claude-sonnet-4-6", cost_usd=0,
    )
    client = AsyncMock()
    client.complete_json = AsyncMock(side_effect=[bad, good])
    out = await classify_submission(
        claude=client, industry="x", brand_name="y", questionnaire={},
    )
    assert out.archetype == "service"
    assert client.complete_json.await_count == 2
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_classify.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/classify.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from app.integrations.anthropic_client import ClaudeClient, MODEL_PRIMARY
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
            cleaned = cleaned[len("json"):]
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
                return ClassifyOutput(archetype="service", confidence=parsed.confidence,
                                      reasoning=parsed.reasoning + " (forced default)")
            return parsed
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            logger.warning("classify attempt {} parse failed: {}", attempt + 1, e)
            user += "\n\nReminder: return JSON only, no prose."
    return ClassifyOutput(archetype="service", confidence=0.0, reasoning="parse_failed")
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_classify.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/classify.py tests/pipeline/__init__.py tests/pipeline/test_classify.py
git commit -m "feat(pipeline): stage 1 classify with retry + low-confidence fallback"
```

---

### Task 21: Stage 2 — `copy`

**Files:**
- Create: `app/pipeline/copy.py`
- Create: `tests/pipeline/test_copy.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from unittest.mock import AsyncMock

import pytest

from app.integrations.anthropic_client import ClaudeResponse
from app.pipeline.copy import write_copy

VALID = {
    "headline": "Hand-tied for every season",
    "subheadline": "Bouquets and arrangements from local growers, designed in-shop daily.",
    "primary_cta": "Order now",
    "secondary_cta": "See bouquets",
    "about": {"heading": "Locally grown", "body": "We source from farms within 50 miles and design every arrangement by hand. Open six mornings a week."},
    "features": [
        {"icon": "leaf", "title": "From local growers", "body": "Every stem is cut within fifty miles of the shop."},
        {"icon": "clock", "title": "Designed daily", "body": "Arrangements are built each morning, never the day before."},
        {"icon": "heart", "title": "Custom bouquets", "body": "Tell us your colors and vibe and we'll design to fit."},
    ],
    "social_proof": [{"text": "Picked up a bouquet for my mum and she still talks about it.", "author": "Sarah K."}],
    "footer_tagline": "Order by noon, delivered same day.",
    "meta": {"title": "Bloom Florist", "description": "Hand-tied bouquets and arrangements from local growers, designed daily in our Brooklyn shop.", "keywords": ["florist", "brooklyn", "bouquet"]},
    "palette_hint": "warm-earth",
}


@pytest.fixture
def fake_claude_good():
    c = AsyncMock()
    c.complete_json = AsyncMock(return_value=ClaudeResponse(
        text=json.dumps(VALID), input_tokens=300, output_tokens=400,
        cache_write_tokens=0, cache_read_tokens=2200,
        model="claude-sonnet-4-6", cost_usd=0.005,
    ))
    return c


async def test_write_copy_happy_path(fake_claude_good):
    submission = {"full_name": "Jane", "email": "j@x.com", "brand_name": "Bloom", "industry": "florist", "questionnaire": {}}
    out = await write_copy(claude=fake_claude_good, archetype="service", submission=submission)
    assert out.headline.startswith("Hand-tied")
    assert len(out.features) == 3


async def test_write_copy_retries_then_escalates_to_opus():
    bad = ClaudeResponse(text="nope", input_tokens=10, output_tokens=2,
                        cache_write_tokens=0, cache_read_tokens=0,
                        model="claude-sonnet-4-6", cost_usd=0)
    good = ClaudeResponse(text=json.dumps(VALID), input_tokens=10, output_tokens=10,
                          cache_write_tokens=0, cache_read_tokens=0,
                          model="claude-opus-4-7", cost_usd=0)
    c = AsyncMock()
    c.complete_json = AsyncMock(side_effect=[bad, bad, good])
    submission = {"full_name": "j", "email": "j@x.com", "brand_name": "B", "industry": "i", "questionnaire": {}}
    out = await write_copy(claude=c, archetype="service", submission=submission)
    assert out.headline.startswith("Hand-tied")
    assert c.complete_json.await_count == 3
    # third call should have used the opus model
    assert c.complete_json.await_args_list[-1].kwargs["model"] == "claude-opus-4-7"
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_copy.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/copy.py`**

```python
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
                user_text=user if i == 0 else user + "\n\nReturn JSON only, matching the schema exactly. No prose.",
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
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_copy.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/copy.py tests/pipeline/test_copy.py
git commit -m "feat(pipeline): stage 2 copy with retry + opus fallback"
```

---

### Task 22: Stage 3 — `images`

**Files:**
- Create: `app/pipeline/images.py`
- Create: `tests/pipeline/test_images.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.integrations.unsplash_client import UnsplashPhoto
from app.pipeline.images import fetch_images_for_archetype


@pytest.fixture
def fake_manifest(tmp_path, monkeypatch):
    archetype_dir = tmp_path / "service"
    archetype_dir.mkdir(parents=True)
    (archetype_dir / "manifest.json").write_text(json.dumps({
        "archetype": "service",
        "image_slots": {
            "hero":      {"query_template": "{industry} pro",       "orientation": "landscape"},
            "feature_1": {"query_template": "{industry} office",    "orientation": "squarish"},
            "feature_2": {"query_template": "{industry} happy",     "orientation": "squarish"},
            "feature_3": {"query_template": "{industry} together",  "orientation": "squarish"},
        }
    }))
    monkeypatch.setattr("app.pipeline.images.TEMPLATES_DIR", tmp_path)
    return tmp_path


async def test_fetch_images_uses_cache_then_unsplash(fake_manifest):
    unsplash = AsyncMock()
    unsplash.search_cached = AsyncMock(return_value=UnsplashPhoto(
        photo_id="p1", url_raw="r", url_regular="reg", url_small="s",
        attribution_html="attr", page_url="pg",
    ))
    fake_db = AsyncMock()

    images = await fetch_images_for_archetype(
        archetype="service", industry="dentist",
        unsplash=unsplash, db=fake_db,
    )
    assert set(images.keys()) == {"hero", "feature_1", "feature_2", "feature_3"}
    assert all(p.photo_id == "p1" for p in images.values())
    assert unsplash.search_cached.await_count == 4


async def test_fetch_images_falls_back_when_unsplash_returns_none(fake_manifest):
    unsplash = AsyncMock()
    unsplash.search_cached = AsyncMock(return_value=None)
    fake_db = AsyncMock()

    images = await fetch_images_for_archetype(
        archetype="service", industry="x",
        unsplash=unsplash, db=fake_db,
    )
    assert all(p is not None for p in images.values())
    # fallback photos use the placeholder photo_id sentinel
    assert all(p.photo_id.startswith("fallback-") for p in images.values())
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_images.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/images.py`**

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger

from app.integrations.unsplash_client import CacheStore, UnsplashClient, UnsplashPhoto

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def _fallback_photo(archetype: str, slot: str) -> UnsplashPhoto:
    # Pre-curated default photos live in the R2 bucket under defaults/<archetype>/<slot>.jpg.
    # When Unsplash returns nothing we point the template at those.
    fallback_url = f"https://defaults.sitesnap.app/{archetype}/{slot}.jpg"
    return UnsplashPhoto(
        photo_id=f"fallback-{archetype}-{slot}",
        url_raw=fallback_url,
        url_regular=fallback_url,
        url_small=fallback_url,
        attribution_html="",
        page_url=fallback_url,
    )


def _load_manifest(archetype: str) -> dict:
    path = TEMPLATES_DIR / archetype / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


async def _fetch_one(
    slot: str, spec: dict, industry: str,
    unsplash: UnsplashClient, db: CacheStore, archetype: str,
) -> tuple[str, UnsplashPhoto]:
    query = spec["query_template"].format(industry=industry)
    orientation = spec.get("orientation", "landscape")
    try:
        photo = await unsplash.search_cached(query, db=db, orientation=orientation)
    except Exception as e:
        logger.warning("unsplash slot={} query={!r} error={}", slot, query, e)
        photo = None
    if photo is None:
        photo = _fallback_photo(archetype, slot)
    return slot, photo


async def fetch_images_for_archetype(
    *, archetype: str, industry: str,
    unsplash: UnsplashClient, db: CacheStore,
) -> dict[str, UnsplashPhoto]:
    manifest = _load_manifest(archetype)
    slots = manifest["image_slots"]
    results = await asyncio.gather(*[
        _fetch_one(slot, spec, industry, unsplash, db, archetype)
        for slot, spec in slots.items()
    ])
    return dict(results)
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_images.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/images.py tests/pipeline/test_images.py
git commit -m "feat(pipeline): stage 3 fetch images (parallel + fallback)"
```

---

### Task 23: Stage 4 — `render`

**Files:**
- Create: `app/pipeline/render.py`
- Create: `tests/pipeline/test_render.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime, timezone

from app.integrations.unsplash_client import UnsplashPhoto
from app.models import CopyOutput
from app.pipeline.render import RenderedSite, render_site

COPY = CopyOutput.model_validate({
    "headline": "Stems and seasons",
    "subheadline": "Hand-tied bouquets from local growers, designed daily.",
    "primary_cta": "Order now",
    "secondary_cta": "See bouquets",
    "about": {"heading": "Locally grown", "body": "We source from farms within fifty miles and design every arrangement by hand each morning."},
    "features": [
        {"icon": "leaf", "title": "From local growers", "body": "Cut within fifty miles."},
        {"icon": "clock", "title": "Designed daily", "body": "Built every morning."},
        {"icon": "heart", "title": "Custom bouquets", "body": "Tell us colors and vibe."},
    ],
    "social_proof": [{"text": "Stunning.", "author": "Sarah K."}],
    "footer_tagline": "Order by noon, delivered same day.",
    "meta": {"title": "Bloom", "description": "Hand-tied bouquets.", "keywords": ["florist"]},
    "palette_hint": "warm-earth",
})

IMAGES = {
    "hero":      UnsplashPhoto("p1", "r", "reg", "s", "attr", "pg"),
    "feature_1": UnsplashPhoto("p2", "r", "reg", "s", "attr", "pg"),
    "feature_2": UnsplashPhoto("p3", "r", "reg", "s", "attr", "pg"),
    "feature_3": UnsplashPhoto("p4", "r", "reg", "s", "attr", "pg"),
}


def test_render_service_produces_html_with_palette_and_copy():
    out = render_site(
        archetype="service", brand_name="Bloom", slug="bloom-x7k2",
        copy=COPY, images=IMAGES, now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert isinstance(out, RenderedSite)
    assert "Stems and seasons" in out.html
    assert "#8B5A3C" in out.html  # warm-earth primary
    assert "From local growers" in out.html
    assert out.palette["primary"] == "#8B5A3C"
    assert "bloom-x7k2" in out.html or "Bloom" in out.html


def test_render_hospitality_works():
    out = render_site(
        archetype="hospitality", brand_name="Loaf", slug="loaf-abcd",
        copy=COPY, images=IMAGES, now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert "Stems and seasons" in out.html
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_render.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/render.py`**

```python
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
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_render.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/render.py tests/pipeline/test_render.py
git commit -m "feat(pipeline): stage 4 render (Jinja2 + palette + asset map)"
```

---

### Task 24: Stage 5 — `publish`

**Files:**
- Create: `app/pipeline/publish.py`
- Create: `tests/pipeline/test_publish.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock

import pytest

from app.pipeline.publish import publish_site


@pytest.fixture
def fake_r2():
    r = AsyncMock()
    r.put_many = AsyncMock()
    return r


@pytest.fixture
def fake_http():
    class FakeResp:
        def __init__(self, content): self.content = content
        def raise_for_status(self): pass

    h = AsyncMock()
    h.get = AsyncMock(return_value=FakeResp(b"\xff\xd8\xff\xe0fake-jpeg"))
    return h


async def test_publish_uploads_html_and_assets(fake_r2, fake_http):
    url = await publish_site(
        slug="bloom-x7k2",
        html="<html>hi</html>",
        assets={"assets/hero.jpg": "https://images.unsplash.com/a", "assets/feature_1.jpg": "https://images.unsplash.com/b"},
        r2=fake_r2, http=fake_http,
    )
    assert url == "https://test.sitesnap.app/bloom-x7k2" or url.endswith("bloom-x7k2")
    fake_r2.put_many.assert_awaited_once()
    uploaded = fake_r2.put_many.await_args.args[0]
    keys = [k for (k, _, _, _) in uploaded]
    assert "sites/bloom-x7k2/index.html" in keys
    assert "sites/bloom-x7k2/assets/hero.jpg" in keys


async def test_publish_returns_correct_subdomain_url(monkeypatch, fake_r2, fake_http):
    monkeypatch.setattr("app.pipeline.publish.settings.r2_public_base", "https://sitesnap.app")
    url = await publish_site(
        slug="x-aaaa", html="<p>x</p>", assets={}, r2=fake_r2, http=fake_http,
    )
    # subdomain or path style, both acceptable as long as slug appears
    assert "x-aaaa" in url
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_publish.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/publish.py`**

```python
from __future__ import annotations

import asyncio
import mimetypes
from urllib.parse import urlparse

import httpx
from loguru import logger

from app.integrations.r2_client import R2Client
from app.settings import settings

HTML_CACHE = "public, max-age=300"
ASSET_CACHE = "public, max-age=31536000, immutable"


def _site_url(slug: str) -> str:
    # Subdomain style: <slug>.<base host>
    parsed = urlparse(settings.r2_public_base)
    host = parsed.netloc or parsed.path  # tolerate URLs without scheme
    scheme = parsed.scheme or "https"
    return f"{scheme}://{slug}.{host}"


async def _download(http: httpx.AsyncClient, url: str) -> bytes:
    resp = await http.get(url, timeout=20.0)
    resp.raise_for_status()
    return resp.content


def _content_type(filename: str) -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or "application/octet-stream"


async def publish_site(
    *,
    slug: str,
    html: str,
    assets: dict[str, str],  # local_filename -> source URL
    r2: R2Client,
    http: httpx.AsyncClient,
) -> str:
    asset_bytes = await asyncio.gather(*[_download(http, url) for url in assets.values()])
    asset_pairs = dict(zip(assets.keys(), asset_bytes))

    items: list[tuple[str, bytes, str, str]] = [
        (f"sites/{slug}/index.html", html.encode("utf-8"), "text/html; charset=utf-8", HTML_CACHE),
    ]
    for local_name, body in asset_pairs.items():
        items.append((
            f"sites/{slug}/{local_name}",
            body,
            _content_type(local_name),
            ASSET_CACHE,
        ))

    await r2.put_many(items)
    url = _site_url(slug)
    logger.info("published slug={} url={}", slug, url)
    return url
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_publish.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/publish.py tests/pipeline/test_publish.py
git commit -m "feat(pipeline): stage 5 publish (download assets + parallel R2 upload)"
```

---

### Task 25: Stage 6 — `notify`

**Files:**
- Create: `app/pipeline/notify.py`
- Create: `tests/pipeline/test_notify.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock

import pytest

from app.pipeline.notify import notify_customer_and_operator


@pytest.fixture
def fake_resend():
    r = AsyncMock()
    r.send = AsyncMock(return_value="msg_c")
    r.send_operator = AsyncMock(return_value="msg_o")
    return r


async def test_notify_sends_both_emails(fake_resend):
    await notify_customer_and_operator(
        resend=fake_resend,
        customer_email="c@example.com",
        customer_name="Jane",
        brand_name="Bloom",
        site_url="https://bloom-x7k2.sitesnap.app",
        archetype="service",
        tokens_in=300, tokens_out=400, cost_usd=0.012,
        slug="bloom-x7k2",
    )
    fake_resend.send.assert_awaited_once()
    fake_resend.send_operator.assert_awaited_once()
    cust_args = fake_resend.send.await_args.kwargs
    assert cust_args["to"] == "c@example.com"
    assert "bloom-x7k2" in cust_args["html"]
    op_args = fake_resend.send_operator.await_args.kwargs
    assert "$0.0120" in op_args["html"] or "0.012" in op_args["html"]
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_notify.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/notify.py`**

```python
from __future__ import annotations

from app.integrations.resend_client import ResendClient

CUSTOMER_HTML = """\
<!doctype html>
<html><body style="font-family: -apple-system, system-ui, sans-serif; background:#FAF6F1; padding:32px;">
  <div style="max-width:560px; margin:0 auto; background:#fff; border-radius:16px; padding:40px; box-shadow:0 8px 32px rgba(0,0,0,.06);">
    <h1 style="margin:0 0 8px; font-size:24px;">Hi {customer_name},</h1>
    <p style="margin:0 0 16px; color:#475569;">Your new site for <strong>{brand_name}</strong> is live.</p>
    <p style="margin:0 0 24px;"><a href="{site_url}" style="background:#1E293B; color:#fff; padding:14px 22px; border-radius:999px; text-decoration:none; display:inline-block; font-weight:600;">View your site</a></p>
    <p style="margin:0 0 8px; font-size:14px; color:#94A3B8;">Direct link:</p>
    <p style="margin:0 0 24px; font-size:14px; word-break:break-all;"><a href="{site_url}" style="color:#1E3A8A;">{site_url}</a></p>
    <hr style="border:none; border-top:1px solid #E2E8F0; margin:24px 0;">
    <p style="margin:0; font-size:13px; color:#94A3B8;">Built with SiteSnap. Reply to this email if you'd like changes.</p>
  </div>
</body></html>
"""

OPERATOR_HTML = """\
<!doctype html>
<html><body style="font-family: -apple-system, system-ui, sans-serif;">
  <h2>New site published</h2>
  <ul>
    <li><strong>Brand:</strong> {brand_name}</li>
    <li><strong>Slug:</strong> {slug}</li>
    <li><strong>URL:</strong> <a href="{site_url}">{site_url}</a></li>
    <li><strong>Archetype:</strong> {archetype}</li>
    <li><strong>Customer:</strong> {customer_name} &lt;{customer_email}&gt;</li>
    <li><strong>Tokens:</strong> {tokens_in} in / {tokens_out} out</li>
    <li><strong>Cost:</strong> ${cost_usd:.4f}</li>
  </ul>
</body></html>
"""


async def notify_customer_and_operator(
    *,
    resend: ResendClient,
    customer_email: str,
    customer_name: str,
    brand_name: str,
    site_url: str,
    archetype: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    slug: str,
) -> None:
    cust_html = CUSTOMER_HTML.format(
        customer_name=customer_name, brand_name=brand_name, site_url=site_url,
    )
    op_html = OPERATOR_HTML.format(
        brand_name=brand_name, slug=slug, site_url=site_url, archetype=archetype,
        customer_name=customer_name, customer_email=customer_email,
        tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost_usd,
    )

    await resend.send(
        to=customer_email,
        subject=f"Your {brand_name} site is live",
        html=cust_html,
    )
    await resend.send_operator(
        subject=f"[sitesnap] new site: {slug}",
        html=op_html,
    )
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_notify.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/notify.py tests/pipeline/test_notify.py
git commit -m "feat(pipeline): stage 6 notify (customer + operator emails)"
```

---

## Phase 6 — Orchestrator

### Task 26: Wire stages together with status + retries

**Files:**
- Create: `app/pipeline/orchestrator.py`
- Create: `tests/pipeline/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.integrations.unsplash_client import UnsplashPhoto
from app.models import ClassifyOutput, CopyOutput
from app.pipeline.orchestrator import generate_site


VALID_COPY = CopyOutput.model_validate({
    "headline": "h", "subheadline": "s",
    "primary_cta": "p", "secondary_cta": "s",
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
})


def _make_deps():
    db = AsyncMock()
    db.fetch_job = AsyncMock(return_value={
        "id": "job1", "submission_id": "sub1", "attempts": 0,
        "status": "queued",
        "claude_tokens_in": 0, "claude_tokens_out": 0, "claude_cost_usd": 0,
    })
    db.fetch_submission = AsyncMock(return_value={
        "id": "sub1",
        "full_name": "Jane Doe", "email": "j@x.com",
        "brand_name": "Bloom", "industry": "florist",
        "questionnaire": {},
    })
    db.update_job_status = AsyncMock()
    db.add_claude_usage = AsyncMock()
    db.increment_attempts = AsyncMock(return_value=1)
    db.slug_exists = AsyncMock(return_value=False)

    classify = AsyncMock(return_value=ClassifyOutput(archetype="service", confidence=0.9, reasoning=""))
    copy_fn = AsyncMock(return_value=VALID_COPY)
    fetch_imgs = AsyncMock(return_value={
        slot: UnsplashPhoto("p", "r", "reg", "s", "a", "pg")
        for slot in ("hero", "feature_1", "feature_2", "feature_3")
    })
    publish = AsyncMock(return_value="https://bloom-x7k2.sitesnap.app")
    notify = AsyncMock()

    return {
        "db": db, "classify": classify, "copy_fn": copy_fn,
        "fetch_imgs": fetch_imgs, "publish": publish, "notify": notify,
    }


async def test_orchestrator_walks_all_stages_to_done(monkeypatch):
    deps = _make_deps()
    monkeypatch.setattr("app.pipeline.orchestrator.classify_submission", deps["classify"])
    monkeypatch.setattr("app.pipeline.orchestrator.write_copy", deps["copy_fn"])
    monkeypatch.setattr("app.pipeline.orchestrator.fetch_images_for_archetype", deps["fetch_imgs"])
    monkeypatch.setattr("app.pipeline.orchestrator.publish_site", deps["publish"])
    monkeypatch.setattr("app.pipeline.orchestrator.notify_customer_and_operator", deps["notify"])

    job_id = uuid4()
    await generate_site(job_id, db=deps["db"], claude=MagicMock(), unsplash=MagicMock(), r2=MagicMock(), http=MagicMock(), resend=MagicMock())

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
    await generate_site(job_id, db=deps["db"], claude=MagicMock(), unsplash=MagicMock(), r2=MagicMock(), http=MagicMock(), resend=MagicMock())

    statuses = [c.args[1] for c in deps["db"].update_job_status.await_args_list]
    assert statuses[-1] == "failed"
    last_kwargs = deps["db"].update_job_status.await_args_list[-1].kwargs
    assert last_kwargs["error_code"] == "copy_invalid_schema"
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/pipeline/test_orchestrator.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/pipeline/orchestrator.py`**

```python
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
        await _set_status(db, job_id, JobStatus.FAILED,
                          error_code="submission_missing", error_message="submission row gone")
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
            archetype=archetype, industry=submission["industry"],
            unsplash=unsplash, db=db,
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
            slug=slug, html=rendered.html,
            assets=rendered.assets_to_download,
            r2=r2, http=http,
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
            db, job_id, JobStatus.FAILED,
            error_code=code, error_message=msg, finished_at_now=True,
        )
        logger.exception("orchestrator: job {} failed: code={} msg={}", job_id, code, msg)
```

- [ ] **Step 4: Run, expect pass**

```bash
uv run pytest tests/pipeline/test_orchestrator.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/pipeline/orchestrator.py tests/pipeline/test_orchestrator.py
git commit -m "feat(pipeline): orchestrator wires 6 stages with status + error mapping"
```

---

## Phase 7 — API endpoints

### Task 27: `POST /api/sites` + `GET /api/jobs/{id}`

**Files:**
- Create: `app/api/sites.py`
- Create: `tests/api/__init__.py`, `tests/api/test_sites.py`

- [ ] **Step 1: Write the failing test**

`tests/api/__init__.py` is empty. `tests/api/test_sites.py`:

```python
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from app.main import create_app

    fake_db = AsyncMock()
    fake_db.insert_submission = AsyncMock(return_value=uuid4())
    fake_db.insert_job = AsyncMock(return_value=uuid4())
    fake_db.fetch_job = AsyncMock(return_value={
        "id": "00000000-0000-0000-0000-000000000000",
        "status": "writing_copy", "progress_pct": 30,
        "site_url": None, "error_code": None, "error_message": None,
    })

    monkeypatch.setattr("app.api.sites.db", fake_db)
    app = create_app()
    return TestClient(app), fake_db


def test_post_sites_returns_202_and_status_url(client):
    c, _ = client
    payload = {
        "full_name": "Jane Doe", "email": "jane@example.com",
        "brand_name": "Bloom", "industry": "florist",
        "questionnaire": {"tone": "warm"},
    }
    r = c.post("/api/sites", json=payload)
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body
    assert body["status_url"].startswith("/status/")


def test_post_sites_rejects_bad_email(client):
    c, _ = client
    r = c.post("/api/sites", json={
        "full_name": "x", "email": "nope", "brand_name": "x", "industry": "x",
    })
    assert r.status_code == 422


def test_get_job_returns_status(client):
    c, _ = client
    r = c.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "writing_copy"
    assert j["progress_pct"] == 30


def test_get_unknown_job_404(client):
    c, fake_db = client
    fake_db.fetch_job = AsyncMock(return_value=None)
    r = c.get("/api/jobs/11111111-1111-1111-1111-111111111111")
    assert r.status_code == 404
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/api/test_sites.py -v
```

Expected: ImportError (no `app.main` yet).

- [ ] **Step 3: Implement `app/api/sites.py`**

```python
from __future__ import annotations

import hashlib
import time
from uuid import UUID

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
    import httpx

    async def _run() -> None:
        async with httpx.AsyncClient() as http:
            await generate_site(
                job_id,
                db=db, claude=claude, unsplash=unsplash, r2=r2,
                http=http, resend=resend_client,
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
```

- [ ] **Step 4: Commit (tests pass after Task 31 wires `create_app`)**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/api/sites.py tests/api/__init__.py tests/api/test_sites.py
git commit -m "feat(api): POST /api/sites and GET /api/jobs/{id}"
```

---

### Task 28: `GET /status/{job_id}` (HTML)

**Files:**
- Create: `app/api/status.py`
- Create: `tests/api/test_status.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient


def test_status_page_renders_for_any_job_id():
    from app.main import create_app
    c = TestClient(create_app())
    r = c.get("/status/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Building your site" in r.text
    assert "00000000-0000-0000-0000-000000000000" in r.text
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/api/test_status.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/api/status.py`**

```python
from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

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
    html = template.render(job_id=str(job_id))
    return HTMLResponse(content=html)
```

- [ ] **Step 4: Run after Task 31, expect pass**

```bash
uv run pytest tests/api/test_status.py -v
```

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/api/status.py tests/api/test_status.py
git commit -m "feat(api): GET /status/{job_id} HTML poller"
```

---

### Task 29: `GET /healthz`

**Files:**
- Create: `app/api/health.py`
- Create: `tests/api/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient


def test_healthz_returns_ok_status_and_dependency_map():
    from app.main import create_app
    c = TestClient(create_app())
    r = c.get("/healthz")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] in ("ok", "degraded")
    assert "dependencies" in j
    assert set(j["dependencies"].keys()) >= {"claude", "supabase", "r2", "unsplash", "resend"}
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/api/test_health.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/api/health.py`**

```python
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
```

- [ ] **Step 4: Run after Task 31, expect pass**

```bash
uv run pytest tests/api/test_health.py -v
```

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/api/health.py tests/api/test_health.py
git commit -m "feat(api): /healthz with dependency map"
```

---

### Task 30: `POST /api/admin/jobs/{id}/retry`

**Files:**
- Create: `app/api/admin.py`
- Create: `tests/api/test_admin.py`

- [ ] **Step 1: Write the failing test**

```python
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from app.main import create_app

    fake_db = AsyncMock()
    fake_db.fetch_job = AsyncMock(return_value={"id": "abc", "status": "failed", "submission_id": "sub1"})
    fake_db.update_job_status = AsyncMock()
    monkeypatch.setattr("app.api.admin.db", fake_db)

    c = TestClient(create_app())
    return c, fake_db


def test_admin_retry_requires_bearer_token(client):
    c, _ = client
    r = c.post("/api/admin/jobs/00000000-0000-0000-0000-000000000000/retry")
    assert r.status_code == 401


def test_admin_retry_rejects_wrong_token(client):
    c, _ = client
    r = c.post(
        "/api/admin/jobs/00000000-0000-0000-0000-000000000000/retry",
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_admin_retry_accepts_correct_token_and_requeues(client):
    c, fake_db = client
    r = c.post(
        "/api/admin/jobs/00000000-0000-0000-0000-000000000000/retry",
        headers={"Authorization": "Bearer test-admin"},
    )
    assert r.status_code == 202
    fake_db.update_job_status.assert_awaited()
```

- [ ] **Step 2: Run, expect fail**

```bash
uv run pytest tests/api/test_admin.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `app/api/admin.py`**

```python
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
        job_id, "queued",
        progress_pct=0, error_code=None, error_message=None,
    )

    from app.integrations.anthropic_client import claude
    from app.integrations.r2_client import r2
    from app.integrations.resend_client import resend_client
    from app.integrations.unsplash_client import unsplash
    from app.pipeline.orchestrator import generate_site

    async def _run() -> None:
        async with httpx.AsyncClient() as http:
            await generate_site(
                job_id, db=db, claude=claude, unsplash=unsplash, r2=r2,
                http=http, resend=resend_client,
            )

    background.add_task(_run)
    return {"job_id": str(job_id), "status": "queued"}
```

- [ ] **Step 4: Run after Task 31, expect pass**

```bash
uv run pytest tests/api/test_admin.py -v
```

- [ ] **Step 5: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/api/admin.py tests/api/test_admin.py
git commit -m "feat(api): admin retry endpoint (bearer-gated)"
```

---

## Phase 8 — App entrypoint

### Task 31: `app/main.py`

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Implement `app/main.py`**

```python
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
        allow_origins=["https://sitesnapbyecm.lovable.app", "https://sitesnap.app", "http://localhost:5173"],
        allow_methods=["POST", "GET", "OPTIONS"],
        allow_headers=["content-type", "authorization"],
    )
    app.include_router(sites.router)
    app.include_router(status.router)
    app.include_router(health.router)
    app.include_router(admin.router)
    return app


app = create_app()
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all previous tests pass; the API tests deferred since Task 27 now succeed.

- [ ] **Step 3: Boot locally and hit `/healthz`**

```bash
uv run uvicorn app.main:app --port 8000
# in another shell:
curl -s http://localhost:8000/healthz
```

Expected: JSON `{"status": "ok"|"degraded", "dependencies": {...}, "env": "local"}`.

- [ ] **Step 4: Commit**

```bash
uv run ruff check app tests && uv run ruff format app tests
git add app/main.py
git commit -m "feat: FastAPI app factory + lifespan + JSON logging"
```

---

## Phase 9 — Cloudflare Worker (subdomain → R2)

### Task 32: Subdomain routing Worker

**Files:**
- Create: `infra/worker/src/index.ts`
- Create: `infra/worker/wrangler.toml`
- Create: `infra/worker/README.md`

> **NOTE:** This is infra glue (not application code). It's the only TypeScript in the project. It exists because Cloudflare's edge network can't natively map `<slug>.sitesnap.app/<path>` → `r2://sitesnap-sites/sites/<slug>/<path>` without a Worker.

- [ ] **Step 1: Write `infra/worker/src/index.ts`**

```typescript
export interface Env {
  SITESNAP_SITES: R2Bucket;
  BASE_DOMAIN: string; // "sitesnap.app"
}

const HTML_CACHE = "public, max-age=300";
const ASSET_CACHE = "public, max-age=31536000, immutable";

function contentTypeFor(key: string): string {
  if (key.endsWith(".html")) return "text/html; charset=utf-8";
  if (key.endsWith(".css")) return "text/css; charset=utf-8";
  if (key.endsWith(".js")) return "application/javascript; charset=utf-8";
  if (key.endsWith(".jpg") || key.endsWith(".jpeg")) return "image/jpeg";
  if (key.endsWith(".png")) return "image/png";
  if (key.endsWith(".webp")) return "image/webp";
  if (key.endsWith(".svg")) return "image/svg+xml";
  if (key.endsWith(".json")) return "application/json";
  return "application/octet-stream";
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);
    const host = url.hostname;
    const base = env.BASE_DOMAIN;

    if (host === base || host === `www.${base}`) {
      // Apex / www: redirect to the marketing site or 404.
      return Response.redirect("https://sitesnapbyecm.lovable.app", 302);
    }

    if (!host.endsWith(`.${base}`)) {
      return new Response("not found", { status: 404 });
    }

    const slug = host.slice(0, -1 * (base.length + 1)); // strip ".<base>"
    if (!slug || slug.includes(".")) {
      return new Response("not found", { status: 404 });
    }

    let path = url.pathname;
    if (path === "/" || path === "") path = "/index.html";

    const key = `sites/${slug}${path}`;
    const object = await env.SITESNAP_SITES.get(key);
    if (!object) {
      return new Response("not found", { status: 404 });
    }

    const headers = new Headers();
    headers.set("Content-Type", contentTypeFor(key));
    headers.set("Cache-Control", key.endsWith(".html") ? HTML_CACHE : ASSET_CACHE);
    headers.set("X-Robots-Tag", "all");
    headers.set("ETag", object.httpEtag);

    return new Response(object.body, { headers });
  },
};
```

- [ ] **Step 2: Write `infra/worker/wrangler.toml`**

```toml
name = "sitesnap-edge"
main = "src/index.ts"
compatibility_date = "2026-01-01"

[vars]
BASE_DOMAIN = "sitesnap.app"

[[r2_buckets]]
binding = "SITESNAP_SITES"
bucket_name = "sitesnap-sites"

[routes]
pattern = "*.sitesnap.app/*"
zone_name = "sitesnap.app"

# After deploying, in the Cloudflare dashboard:
#   1. Add wildcard CNAME *.sitesnap.app -> <worker route target>
#   2. Ensure SSL/TLS is Full (strict) and "Edge Certificates" includes the wildcard
```

- [ ] **Step 3: Write `infra/worker/README.md`**

```markdown
# sitesnap-edge

Cloudflare Worker that maps `<slug>.sitesnap.app/<path>` to `r2://sitesnap-sites/sites/<slug>/<path>`.

## Deploy (one-time + on changes)

```bash
cd infra/worker
npm i -g wrangler
wrangler login
wrangler r2 bucket create sitesnap-sites    # only if it doesn't exist
wrangler deploy
```

## DNS setup (one-time, in Cloudflare dashboard)

1. Add the zone `sitesnap.app` to your Cloudflare account.
2. Add a wildcard DNS record: `*` of type `CNAME` pointing to anything (the worker route takes over). Proxy status = on.
3. Confirm "Edge Certificates" covers `*.sitesnap.app` (CF auto-provisions this).
4. The `wrangler.toml` `routes` block creates `*.sitesnap.app/*` route on deploy.

## Sanity check

After deploying and uploading a test site (`sites/test-1234/index.html`) to R2:

```bash
curl -I https://test-1234.sitesnap.app/
```

Expected: `200 OK`, `content-type: text/html`, `cache-control: public, max-age=300`.
```

- [ ] **Step 4: Commit**

```bash
git add infra/worker
git commit -m "feat(infra): cloudflare worker for subdomain -> R2 routing"
```

---

## Phase 10 — Deploy config

### Task 33: Dockerfile, render.yaml, README

**Files:**
- Create: `Dockerfile`
- Create: `render.yaml`
- Create: `README.md`

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY templates ./templates
COPY prompts ./prompts
COPY migrations ./migrations

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Write `render.yaml`**

```yaml
services:
  - type: web
    name: sitesnap-backend
    runtime: docker
    plan: starter
    region: oregon
    dockerfilePath: ./Dockerfile
    healthCheckPath: /healthz
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: UNSPLASH_ACCESS_KEY
        sync: false
      - key: SUPABASE_DB_URL
        sync: false
      - key: R2_ACCOUNT_ID
        sync: false
      - key: R2_ACCESS_KEY_ID
        sync: false
      - key: R2_SECRET_ACCESS_KEY
        sync: false
      - key: R2_BUCKET
        value: sitesnap-sites
      - key: R2_PUBLIC_BASE
        value: https://sitesnap.app
      - key: RESEND_API_KEY
        sync: false
      - key: RESEND_FROM_EMAIL
        value: hello@sitesnap.app
      - key: RESEND_OPERATOR_EMAIL
        value: devops@branchlead.com
      - key: ADMIN_BEARER_TOKEN
        sync: false
      - key: SENTRY_DSN
        sync: false
      - key: LOG_LEVEL
        value: INFO
      - key: ENV
        value: production
```

- [ ] **Step 3: Write `README.md`**

```markdown
# SiteSnap Backend

Python FastAPI service that turns a form submission into a hosted single-page website in ~60 seconds.

## Quick start

```bash
uv sync
cp .env.example .env  # fill in your keys
psql "$SUPABASE_DB_URL" -f migrations/0001_init.sql
psql "$SUPABASE_DB_URL" -f migrations/0002_unsplash_cache.sql
uv run uvicorn app.main:app --reload --port 8000
```

POST a submission:

```bash
curl -X POST http://localhost:8000/api/sites \
  -H 'content-type: application/json' \
  -d '{"full_name":"Jane Doe","email":"jane@example.com","brand_name":"Bloom","industry":"florist","questionnaire":{"tone":"warm"}}'
```

Open the returned `status_url` in a browser.

## Testing

```bash
uv run pytest -v          # unit + pipeline + api tests (mocked I/O)
RUN_DB_TESTS=1 uv run pytest tests/integrations/test_db.py  # live DB roundtrip
```

## Deployment

- **Backend** → Render (Docker). `git push origin main` triggers the deploy.
- **Edge worker** → Cloudflare. `cd infra/worker && wrangler deploy`.
- **Migrations** → apply with `psql` or `supabase db push`.

See [`docs/superpowers/specs/2026-05-23-sitesnap-mvp-backend-design.md`](docs/superpowers/specs/2026-05-23-sitesnap-mvp-backend-design.md) for the full architecture.
```

- [ ] **Step 4: Run the full suite one last time**

```bash
uv run ruff check . && uv run ruff format .
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile render.yaml README.md
git commit -m "chore(deploy): Dockerfile, render.yaml blueprint, README"
```

---

## Done

After Task 33:

- Code is feature-complete for the MVP slice defined in the spec.
- A real submission to `POST /api/sites` runs the pipeline end-to-end and emails a live URL.
- Render auto-deploys on `git push origin main`.
- Generated sites are live at `https://<slug>.sitesnap.app` once the CF Worker is deployed and DNS is configured.

### Post-build manual checks

1. `curl https://api.sitesnap.app/healthz` returns `status: ok`.
2. POST a submission with curl from a non-dev machine; verify the email arrives.
3. Open the generated site URL in mobile + desktop; verify layout, palette, photo licence attribution.
4. Operator email arrives in `devops@branchlead.com`.

### Known follow-ups (out of MVP, each gets its own spec)

- Stripe checkout + tier gating.
- Custom domains for Pro tier (CF Custom Hostnames API).
- Multi-page sites.
- AI image generation as opt-in upgrade.
- User accounts + dashboard.
- Stuck-job sweeper (cron) once we add Redis/arq.

