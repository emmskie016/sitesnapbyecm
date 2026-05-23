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
