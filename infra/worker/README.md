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
