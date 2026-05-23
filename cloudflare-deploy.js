/**
 * cloudflare-deploy.js
 * Deploys generated website files to Cloudflare Pages via the Direct Upload API.
 *
 * Two exports:
 *   createCloudflarePagesProject — one-time setup, run once before first deploy
 *   deploySiteToCloudflarPages   — called for every generated site
 *
 * Also contains the n8n Code node body at the bottom (paste into n8n).
 */

/**
 * One-time setup: create the Cloudflare Pages project that will host all sites.
 * Run this manually from Node.js ONCE before the first deployment.
 *
 * @param {string} accountId   - CF account ID
 * @param {string} apiToken    - CF API token with Pages:Edit permission
 * @param {string} projectName - The project slug, e.g. "sitesnap-sites"
 * @returns {Object} The created project object from the CF API
 */
async function createCloudflarePagesProject(accountId, apiToken, projectName) {
  const response = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/pages/projects`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type':  'application/json',
      },
      body: JSON.stringify({
        name:              projectName,
        production_branch: 'main',
      }),
    }
  );

  const data = await response.json();

  if (!response.ok || !data.success) {
    throw new Error(
      `createCloudflarePagesProject failed: ${JSON.stringify(data.errors || data)}`
    );
  }

  console.log(`Project created: ${data.result.subdomain}`);
  return data.result;
}

/**
 * Deploys a set of files to Cloudflare Pages using the Direct Upload API.
 * Constructs a multipart/form-data body manually (no external dependencies).
 *
 * @param {Object} files       - { "index.html": "<html>...", "style.css": "..." }
 * @param {string} accountId
 * @param {string} apiToken
 * @param {string} projectName
 * @returns {string} The live deployment URL, e.g. https://abc123.sitesnap-sites.pages.dev
 */
async function deploySiteToCloudflarePages(files, accountId, apiToken, projectName) {
  // Build raw multipart body without any external packages
  const boundary = `----SiteSnapBoundary${Date.now()}${Math.random().toString(36).slice(2)}`;
  const CRLF     = '\r\n';
  const parts    = [];

  const mimeType = (filename) => {
    if (filename.endsWith('.css'))  return 'text/css; charset=utf-8';
    if (filename.endsWith('.js'))   return 'application/javascript; charset=utf-8';
    if (filename.endsWith('.json')) return 'application/json';
    return 'text/html; charset=utf-8';
  };

  for (const [filename, content] of Object.entries(files)) {
    parts.push(
      `--${boundary}${CRLF}` +
      `Content-Disposition: form-data; name="${filename}"; filename="${filename}"${CRLF}` +
      `Content-Type: ${mimeType(filename)}${CRLF}` +
      CRLF +
      content +
      CRLF
    );
  }

  parts.push(`--${boundary}--${CRLF}`);
  const bodyString = parts.join('');

  const response = await fetch(
    `https://api.cloudflare.com/client/v4/accounts/${accountId}/pages/projects/${projectName}/deployments`,
    {
      method:  'POST',
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type':  `multipart/form-data; boundary=${boundary}`,
      },
      body: bodyString,
    }
  );

  const data = await response.json();

  if (!response.ok || !data.success) {
    throw new Error(
      `Cloudflare Pages deployment failed (${response.status}): ${JSON.stringify(data.errors || data)}`
    );
  }

  // CF Pages returns the canonical URL in result.url for direct uploads
  const deploymentId  = data.result.id;
  const deploymentUrl = data.result.url ||
    `https://${deploymentId}.${projectName}.pages.dev`;

  return { deploymentUrl, deploymentId };
}

// ── n8n Code node body ───────────────────────────────────────────────────────
// Paste everything between the dashes into the n8n "Deploy to Cloudflare" Code node.
// Remove the module.exports block at the bottom.
// ---------------------------------------------------------------------------

const { files, formData, recordId, requestId } = $input.item.json;

const cfAccountId   = $env.CF_ACCOUNT_ID;
const cfApiToken    = $env.CF_API_TOKEN;
const cfProjectName = $env.CF_PROJECT_NAME;

const boundary = `----SiteSnapBoundary${Date.now()}${Math.random().toString(36).slice(2)}`;
const CRLF     = '\r\n';
const parts    = [];

const mimeType = (filename) => {
  if (filename.endsWith('.css'))  return 'text/css; charset=utf-8';
  if (filename.endsWith('.js'))   return 'application/javascript; charset=utf-8';
  if (filename.endsWith('.json')) return 'application/json';
  return 'text/html; charset=utf-8';
};

for (const [filename, content] of Object.entries(files)) {
  parts.push(
    `--${boundary}${CRLF}` +
    `Content-Disposition: form-data; name="${filename}"; filename="${filename}"${CRLF}` +
    `Content-Type: ${mimeType(filename)}${CRLF}` +
    CRLF +
    content +
    CRLF
  );
}
parts.push(`--${boundary}--${CRLF}`);

const response = await fetch(
  `https://api.cloudflare.com/client/v4/accounts/${cfAccountId}/pages/projects/${cfProjectName}/deployments`,
  {
    method:  'POST',
    headers: {
      'Authorization': `Bearer ${cfApiToken}`,
      'Content-Type':  `multipart/form-data; boundary=${boundary}`,
    },
    body: parts.join(''),
  }
);

const data = await response.json();

if (!response.ok || !data.success) {
  throw new Error(
    `Cloudflare Pages deployment failed (${response.status}): ${JSON.stringify(data.errors || data)}`
  );
}

const deploymentId  = data.result.id;
const deploymentUrl = data.result.url ||
  `https://${deploymentId}.${cfProjectName}.pages.dev`;

return [{ json: { deploymentUrl, deploymentId, formData, recordId, requestId } }];

// ---------------------------------------------------------------------------

// ── Local testing only ───────────────────────────────────────────────────────
if (typeof module !== 'undefined') {
  module.exports = { createCloudflarePagesProject, deploySiteToCloudflarePages };
}
