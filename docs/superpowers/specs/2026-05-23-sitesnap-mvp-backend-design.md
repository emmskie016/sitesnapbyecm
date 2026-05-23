# SiteSnap MVP Backend — Design

**Status:** Draft — pending user review
**Author:** Emmerson Morales (devops@branchlead.com)
**Date:** 2026-05-23
**Project:** sitesnap-backend
**Frontend:** [sitesnapbyecm.lovable.app](https://sitesnapbyecm.lovable.app)

---

## 1. Problem

SiteSnap is an AI-powered website builder. A visitor fills a 2-minute questionnaire on the marketing site (`sitesnapbyecm.lovable.app`) and is promised a custom, hosted, mobile-responsive single-page website within 60 seconds, with the live URL emailed to them.

Today only the Lovable marketing site exists. There is **no backend**. This spec defines the first production-shippable backend slice: a Python service that takes the form submission and delivers a live URL.

## 2. Scope

### In scope (MVP)

- HTTP API to accept the questionnaire submission from the Lovable frontend.
- Generation pipeline that turns a submission into a finished single-page website (HTML + CSS + images).
- Publishing the generated site to a unique subdomain (`<slug>.sitesnap.app`).
- A status page the user lands on after submitting, with live progress and the final URL.
- A confirmation email containing the live URL.
- An operator notification email for every published site.

### Explicitly out of scope (each gets its own future spec)

1. Payments and pricing-tier gating ($29 Starter / $59 Pro / $149 Agency).
2. Custom domains for the Pro tier.
3. Multi-page sites.
4. AI-generated imagery (Unsplash only for MVP).
5. User accounts, login, "my sites" dashboard.
6. Site editing after generation (one-shot only).
7. Analytics injection into generated sites.
8. Per-site sitemap.xml / robots.txt.
9. Automated a11y audit gate.

## 3. Success criteria

- **Latency:** p95 form-submit-to-live-URL ≤ 45 seconds. p50 ≤ 25 seconds. The 60-second marketing promise has headroom.
- **Quality:** Generated sites are visually distinct (3 archetypes × 4 palettes = 12 visual identities) and do not look like generic GPT-produced HTML.
- **Reliability:** ≥ 95% of submissions complete without manual intervention. Failures degrade gracefully (fallback images, retry with stronger model).
- **Cost ceiling:** ≤ $0.15 per generated site in marginal LLM + infra cost.

## 4. Architecture

### 4.1 Stack

| Concern | Choice | Reason |
|---|---|---|
| Language / framework | Python 3.12 + FastAPI + uvicorn | User-mandated Python; FastAPI is the obvious modern Python web framework. |
| Backend host | Render | User-selected. Managed deploys, simple env management. |
| Database | Supabase Postgres | User-selected. Already in user's stack per memory. |
| Job execution | FastAPI `BackgroundTasks` (in-process) | MVP traffic doesn't justify Redis + worker dyno. Upgrade path documented in §10. |
| LLM | Anthropic Claude (`sonnet-4-6` workhorse, `opus-4-7` fallback) | User-selected. Matches user's production stack. |
| Image source | Unsplash API | User-selected. License-clean photos, free tier. |
| Site hosting | Cloudflare R2 (object storage) | User-selected. Free egress, S3-compatible. |
| Subdomain routing | Cloudflare Worker (TypeScript, ~20 lines) | User accepted as infra glue, not application code. |
| Email | Resend | User-selected. Modern Python SDK. |
| Templating | Jinja2 with `autoescape=True` | Standard, well-understood, no client-side JS for generated sites. |
| Image processing | Pillow | Resize Unsplash photos for responsive `srcset`. |

### 4.2 End-to-end flow

```
Lovable form
   │  POST /api/sites (questionnaire JSON)
   ▼
FastAPI: validate → INSERT submission, INSERT job(status=queued) → return 202 {job_id, status_url}
   │
   ├─→ HTTP 202 to client → client redirects browser to /status/<job_id>
   │
   └─→ BackgroundTasks.add_task(orchestrator.generate_site, job_id)
            │
            ▼
       Six-stage pipeline (writes to jobs.status, jobs.progress_pct after each stage):
         1. classifying        Claude picks archetype                 (10%)
         2. writing_copy       Claude generates structured copy JSON  (30%)
         3. fetching_images    Unsplash search per slot (parallel)    (50%)
         4. rendering          Jinja2 + Pillow                        (70%)
         5. publishing         aioboto3 upload to R2                  (90%)
         6. notifying          Resend customer + operator emails      (100%)
            │
            ▼
   Client polls GET /api/jobs/<job_id> every 2s → sees status → shows live URL on done
   Generated site is live at https://<slug>.sitesnap.app
```

### 4.3 Latency budget

| Stage | p50 | p95 |
|---|---:|---:|
| classifying | 1.5s | 3s |
| writing_copy | 7s | 12s |
| fetching_images | 2s | 4s |
| rendering | 2s | 4s |
| publishing | 2s | 5s |
| notifying | 1s | 2s |
| **Total** | **~15.5s** | **~30s** |

The 60-second marketing promise has ~30s of headroom at p95.

## 5. Data model (Supabase / Postgres)

Two tables. The form input is immutable; the job state is mutable and retry-capable.

```sql
-- submissions: immutable form input
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
  -- idempotency: sha256(email || brand_name || floor(epoch_seconds / 60))
  -- dedupes accidental double-submit within 60 seconds
  request_hash  text unique
);

create index submissions_email_idx on submissions(email, created_at desc);

-- jobs: generation state machine, one row per attempt
create table jobs (
  id                 uuid primary key default gen_random_uuid(),
  submission_id      uuid not null references submissions(id) on delete cascade,
  status             text not null default 'queued',
    -- 'queued' | 'classifying' | 'writing_copy' | 'fetching_images'
    -- | 'rendering' | 'publishing' | 'notifying' | 'done' | 'failed'
  progress_pct       int  not null default 0,
  archetype          text,    -- 'service' | 'hospitality' | 'portfolio'
  slug               text unique,
  palette            jsonb,   -- {primary, accent, neutral, ink}
  site_url           text,
  error_code         text,
  error_message      text,
  attempts           int  not null default 0,
  claude_tokens_in   int  not null default 0,
  claude_tokens_out  int  not null default 0,
  claude_cost_usd    numeric(10,4) not null default 0,
  created_at         timestamptz not null default now(),
  started_at         timestamptz,
  finished_at        timestamptz
);

create index jobs_active_idx
  on jobs(status, created_at)
  where status not in ('done','failed');
create index jobs_submission_idx on jobs(submission_id);

-- unsplash_cache: dedupe popular image lookups
create table unsplash_cache (
  query        text primary key,
  photo_id     text not null,
  urls         jsonb not null,    -- {raw, full, regular, small, thumb}
  fetched_at   timestamptz not null default now()
);

create index unsplash_cache_fetched_idx on unsplash_cache(fetched_at);
-- entries older than 90 days are refreshed on read
```

**Notable choices:**

- `request_hash` minute-bucketed → dedupes Lovable's network retries without forcing strict exactly-once.
- `jobs.status` as a string state machine with a partial index for the active set. Postgres `enum` types are painful to alter; `text` + a future `CHECK` is cheaper.
- `progress_pct` is denormalized from `status` so the polling UI doesn't need to know stage names.
- `slug` lives on `jobs`, not `submissions` — a retried job picks a fresh slug; failed slugs never go live.
- No `users` table, no auth. Status URL relies on the unguessable `job_id` UUID. No PII is exposed by `GET /api/jobs/<id>` (status, progress, URL only).
- Backend uses Supabase service-role key; RLS is unused for MVP (no user-facing query path).
- No `events` table. `jobs` columns + structured logs cover MVP observability.

## 6. Generation pipeline

### 6.1 Stage 1 — `classifying` (10%)

- **Call:** Claude `sonnet-4-6`, tool-use JSON mode.
- **Input:** Submission's `industry`, `brand_name`, `questionnaire`.
- **Output schema:** `{archetype: 'service'|'hospitality'|'portfolio', confidence: float, reasoning: string}`.
- **Prompt caching:** System prompt holds the three archetype definitions (~1500 tokens) — cached, 5-min TTL hits any traffic above 12/hr.
- **Fallback:** `confidence < 0.6` → default to `service`.

### 6.2 Stage 2 — `writing_copy` (30%)

- **Call:** Claude `sonnet-4-6`, structured JSON output.
- **Input:** Submission + chosen archetype.
- **Output schema** (validated by Pydantic):

  ```json
  {
    "headline": "...",
    "subheadline": "...",
    "primary_cta": "...",
    "secondary_cta": "...",
    "about": {"heading": "...", "body": "..."},
    "features": [
      {"icon": "leaf", "title": "...", "body": "..."},
      {"icon": "...", "title": "...", "body": "..."},
      {"icon": "...", "title": "...", "body": "..."}
    ],
    "social_proof": [{"text": "...", "author": "..."}],
    "footer_tagline": "...",
    "meta": {"title": "...", "description": "...", "keywords": ["..."]},
    "palette_hint": "warm-earth | cool-modern | bold-vibrant | muted-elegant"
  }
  ```

- **Retry ladder:** parse failure → 1 retry with stricter system prompt → escalate to `opus-4-7` → fail with `error_code='copy_invalid_schema'`.
- **Cached prompts:** `prompts/system_copywriter.md` plus `prompts/archetype_<archetype>.md`.

### 6.3 Stage 3 — `fetching_images` (50%)

- Each archetype manifest declares image slots with keyword sets:
  - `service`: 1 hero + 3 feature thumbnails
  - `hospitality`: 1 hero + 3 gallery shots
  - `portfolio`: 1 hero + 3 case-study thumbnails
- **Parallelization:** `asyncio.gather` across all slots — single wall-clock step.
- **Cache:** `unsplash_cache` table keyed on query string; entries < 90 days reused.
- **Fallback:** on Unsplash rate limit / empty result, use pre-curated default photo from `r2://defaults/<archetype>/<slot>.jpg`. The site always ships.

### 6.4 Stage 4 — `rendering` (70%)

- Jinja2 with `autoescape=True`.
- Three archetype directories under `templates/`:
  - `service/`, `hospitality/`, `portfolio/`, each with `index.html.j2`, `styles.css.j2`, `manifest.json`, `static/`.
- **Palettes are curated, not LLM-generated.** `palette_hint` maps to one of 4 hand-designed palette dicts per archetype (12 total in `app/palettes.py`). LLM-generated CSS produces AI-slop; curated palettes look distinctive.
- Hero images downloaded from Unsplash, resized with Pillow to 1600/800/400px widths for responsive `<img srcset>`.
- Generated sites contain **no JavaScript**. Inline `<style>` for critical CSS, external `styles.css` for the rest.

### 6.5 Stage 5 — `publishing` (90%)

- **Slug:** `slugify(brand_name) + "-" + nanoid(4)` (e.g. `bloom-florist-x7k2`). Collision check vs `jobs.slug` unique index; regenerate on collision (max 5 attempts before giving up with `error_code='slug_collision'`).
- **R2 layout:** `sites/<slug>/{index.html, styles.css, assets/...}`.
- **Upload:** concurrent via `aioboto3` (R2 is S3-compatible).
- **Cache-Control:** `public, max-age=31536000, immutable` on hashed assets; `public, max-age=300` on `index.html`.

### 6.6 Stage 6 — `notifying` (100%)

- Resend Python SDK sends two emails:
  - **Customer:** branded HTML containing the live URL.
  - **Operator** (devops@branchlead.com): summary with slug, archetype, tokens, cost.
- Idempotent on `notifying → done` transition; checked via `finished_at IS NULL` predicate.
- Set `status='done'`, `finished_at=now()`.

### 6.7 Retry & failure model

Each stage runs inside `try/except`. On error: increment `attempts`, write `error_code` + `error_message`.

**Retryable errors** (`claude_rate_limit`, `unsplash_5xx`, `r2_5xx`, `resend_5xx`): reschedule via `BackgroundTasks` with exponential backoff (5s → 15s → 45s). Cap at `attempts=3`.

**Non-retryable errors** (`copy_invalid_schema` after Opus fallback, `r2_credentials`, `bad_input`, `slug_collision`): fail fast, `status='failed'`. The customer is **not** auto-emailed on hard failure — operator triages manually for MVP.

A stuck-job sweeper is out of scope for MVP. The admin endpoint `POST /api/admin/jobs/{id}/retry` is sufficient for manual recovery.

## 7. API surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sites` | Form intake. Returns `202 {job_id, status_url}`. Validates with Pydantic. `400` on invalid input, `409` on `request_hash` duplicate, `429` on IP rate limit (10/hr default). |
| `GET` | `/api/jobs/{job_id}` | JSON status for polling. Returns `{status, progress_pct, site_url, error}`. `Cache-Control: no-store`. `404` if unknown. |
| `GET` | `/status/{job_id}` | Server-rendered HTML status page (`templates/status.html.j2`). Vanilla JS poller (2s) with progress bar; reveals live URL on `done`. |
| `GET` | `/healthz` | Liveness + dependency probe. `{status, dependencies: {claude, supabase, r2, unsplash, resend}}`. Used by Render. |
| `POST` | `/api/admin/jobs/{id}/retry` | Bearer-token-gated retry endpoint for failed jobs. |

The Lovable frontend update is small: the form's submit handler POSTs JSON to `https://api.sitesnap.app/api/sites`, then redirects the browser to the returned `status_url`.

## 8. Repo layout

```
sitesnap-backend/
├── pyproject.toml              # uv-managed, Python 3.12
├── .env.example                # documents all required env vars
├── Dockerfile                  # for Render
├── render.yaml                 # blueprint: web service + env
├── app/
│   ├── main.py                 # FastAPI app + lifespan
│   ├── api/
│   │   ├── sites.py            # POST /api/sites, GET /api/jobs/{id}
│   │   ├── status.py           # GET /status/{id} (Jinja HTML)
│   │   ├── health.py           # /healthz
│   │   └── admin.py            # /api/admin/jobs/{id}/retry
│   ├── pipeline/
│   │   ├── orchestrator.py     # generate_site(job_id) — runs all 6 stages
│   │   ├── classify.py         # stage 1
│   │   ├── copy.py             # stage 2
│   │   ├── images.py           # stage 3
│   │   ├── render.py           # stage 4
│   │   ├── publish.py          # stage 5
│   │   └── notify.py           # stage 6
│   ├── integrations/
│   │   ├── anthropic_client.py # cached system prompts, retry, cost telemetry
│   │   ├── unsplash_client.py  # rate-limit aware, cache-through
│   │   ├── r2_client.py        # aioboto3 wrapper
│   │   ├── resend_client.py    # transactional email
│   │   └── supabase_client.py  # asyncpg or supabase-py
│   ├── models.py               # Pydantic schemas
│   ├── slugs.py                # slug generation + collision retry
│   ├── palettes.py             # the 12 curated palette dicts
│   └── settings.py             # pydantic-settings
├── templates/
│   ├── service/    { index.html.j2, styles.css.j2, manifest.json, static/ }
│   ├── hospitality/{ ... }
│   ├── portfolio/  { ... }
│   └── status.html.j2          # the polling status page
├── prompts/
│   ├── system_classifier.md
│   ├── system_copywriter.md
│   ├── archetype_service.md
│   ├── archetype_hospitality.md
│   └── archetype_portfolio.md
├── migrations/                 # SQL migrations
│   ├── 0001_init.sql
│   └── 0002_unsplash_cache.sql
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── pipeline/
│   └── fixtures/
└── infra/
    └── worker/                 # CF Worker (TS) — subdomain → bucket routing
        ├── src/index.ts        # ~20 lines
        ├── wrangler.toml
        └── README.md
```

## 9. Configuration (env vars)

```
ANTHROPIC_API_KEY
UNSPLASH_ACCESS_KEY
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
R2_ACCOUNT_ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_BUCKET=sitesnap-sites
R2_PUBLIC_BASE=https://sitesnap.app
RESEND_API_KEY
RESEND_FROM_EMAIL=hello@sitesnap.app
RESEND_OPERATOR_EMAIL=devops@branchlead.com
ADMIN_BEARER_TOKEN
SENTRY_DSN          # optional
LOG_LEVEL=INFO
```

`pydantic-settings` loads these; the app refuses to boot if any required variable is missing.

## 10. Operational concerns

### 10.1 Local dev

```bash
uv sync
cp .env.example .env            # fill keys
supabase db push                # apply SQL migrations to local or dev Supabase
uv run uvicorn app.main:app --reload --port 8000
```

Migrations are raw SQL under `migrations/` (no Alembic). The Supabase CLI applies them in order; rollbacks are written as new forward migrations rather than down-scripts.

### 10.2 Deploy

- **Backend → Render:** `render.yaml` blueprint, deploy on `git push origin main`. Build `uv sync --frozen`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check `/healthz`.
- **Worker → Cloudflare:** `cd infra/worker && wrangler deploy`. Wildcard DNS `*.sitesnap.app` → Worker via CF dashboard (one-time setup).
- **Migrations:** Supabase CLI in CI on merge to main. First migration applied manually to bootstrap.

### 10.3 Observability

- **Structured logs** (loguru → JSON), one line per stage transition: `{job_id, stage, duration_ms, tokens_in, tokens_out, cost_usd}`.
- **Sentry** for exceptions (optional but recommended).
- **Render metrics** are enough for MVP.
- **Operator email** on every published site doubles as a real-time pulse.

### 10.4 Upgrade path past MVP

When traffic exceeds ~100 sites/day, or when generation jobs grow beyond ~60s, add a Redis instance and an `arq` worker dyno on Render. `BackgroundTasks` invocations swap to `arq.enqueue_job`; orchestrator code is otherwise unchanged because all state is in Postgres.

## 11. Testing strategy

- **Unit tests** (~50ms each): slug generation, palette resolution, Pydantic validation, prompt assembly.
- **Integration tests:** FastAPI `TestClient` + ephemeral Supabase schema. External APIs mocked via `respx`. Happy-path coverage of each stage.
- **Pipeline tests:** VCR-recorded Claude + Unsplash responses → full pipeline against a dev R2 bucket → assert rendered HTML validates, all asset URLs resolve, palette CSS variables present.
- **Smoke test in prod:** post-deploy `pytest tests/smoke.py` hits `/healthz` and runs one synthetic generation (`is_synthetic=true` job that skips email).
- **No browser/E2E test** for MVP — the status page is small enough to verify manually.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Claude rate-limit during a traffic spike | Exponential backoff, Opus fallback, prompt caching to cut TPM consumption. |
| Unsplash rate-limit (50 req/hr free) | Cache table + pre-curated fallbacks per archetype. |
| Cloudflare Worker subdomain DNS not propagating | One-time `wrangler` deploy + wildcard `*.sitesnap.app` CNAME; validated in `/healthz`. |
| Generated copy hallucinates client claims | System prompt forbids unverifiable claims; copy is generic positioning, not made-up testimonials. (Note: `social_proof` is generic; we do not invent named customers.) |
| Job lost on Render dyno restart mid-generation | MVP accepts this loss; admin retry endpoint recovers. Real fix lives in §10.4. |
| Domain `sitesnap.app` not yet purchased | Pre-requisite for go-live; non-blocking for code completion. |

## 13. Open questions

None blocking. Documenting non-decisions:

- The Lovable form's exact JSON shape is assumed to match `{full_name, email, brand_name, industry, questionnaire: {...}}`. To be confirmed against the live Lovable form before integration; may need a small adapter.
- The 3 archetype boundaries (service / hospitality / portfolio) are defensible but not researched against actual incoming traffic. After ~20 real submissions, revisit archetype coverage.
- Domain ownership of `sitesnap.app` is assumed; if unavailable, the project picks a different domain and `R2_PUBLIC_BASE` is reconfigured.

## 14. Next step

After approval of this spec, invoke the `writing-plans` skill to produce a step-by-step implementation plan with file-level tasks and review checkpoints.
