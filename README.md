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
