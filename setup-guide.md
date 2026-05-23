# SiteSnap Backend — Setup Guide

Complete step-by-step instructions for wiring up every service.
Follow the steps in order; each section builds on the last.

---

## Prerequisites

- A Lovable site with the multi-step form already built and ready to submit JSON
- A Google account (for Gmail sending)
- A credit/debit card on file with Cloudflare (free tier, no charge)
- An Anthropic account with API access

---

## 1. Airtable Setup

### 1a. Create the base

1. Log in at [airtable.com](https://airtable.com).
2. Click **Add a base → Start from scratch**.
3. Name the base **SiteSnap**.
4. Rename the default table to **Website Requests**.

### 1b. Add all fields

Delete the default fields (except Name), then add these in order:

| Field Name | Type | Notes |
|---|---|---|
| Full Name | Single line text | Rename the default "Name" field |
| Email Address | Email | |
| Business / Brand Name | Single line text | |
| Industry / Niche | Single line text | |
| Website Type | Single select | Options: Business Website, Portfolio, Landing Page, Other |
| Pages / Sections Needed | Multiple select | Options: Home, About, Services, Portfolio, Testimonials, Contact, Blog, FAQ, Pricing |
| Design Style | Single select | Options: Clean & Minimal, Bold & Modern, Elegant & Luxury, Playful & Fun, Corporate & Professional |
| Color Preferences | Single line text | |
| Tone / Voice | Single select | Options: Friendly, Professional, Bold, Playful, Elegant |
| Tagline or Headline | Long text | |
| Services or Offerings | Long text | |
| About / Bio | Long text | |
| Social Media Links | Single line text | |
| Example Sites They Like | Single line text | |
| Anything Else | Long text | |
| Plan Selected | Single select | Options: Starter, Pro, Agency |
| Generated Site URL | URL | |
| Status | Single select | Options: Pending, Generating, Live, Failed |
| Created At | Created time | Auto-set by Airtable |

### 1c. Get your API credentials

1. Go to [airtable.com/create/tokens](https://airtable.com/create/tokens).
2. Click **Create new token**.
3. Give it a name (e.g. `sitesnap-n8n`).
4. Set scopes: `data.records:read`, `data.records:write`, `schema.bases:read`.
5. Under **Access**, select the **SiteSnap** base.
6. Click **Create token** and copy it immediately → this is your `AIRTABLE_API_KEY`.
7. Open your SiteSnap base. The URL looks like:
   `https://airtable.com/appXXXXXXXXXXXXXX/...`
   Copy the `appXXXXXXXXXXXXXX` part → this is your `AIRTABLE_BASE_ID`.

---

## 2. Cloudflare Pages Setup

### 2a. Create a Cloudflare account

If you don't already have one, sign up at [dash.cloudflare.com](https://dash.cloudflare.com).
The free plan is sufficient.

### 2b. Get your Account ID

1. Log in to the Cloudflare dashboard.
2. Click on any domain, or go to the Workers & Pages overview.
3. In the right sidebar, find **Account ID** → copy it → this is your `CF_ACCOUNT_ID`.

### 2c. Create an API token

1. Go to **My Profile → API Tokens → Create Token**.
2. Click **Use template** → **Edit Cloudflare Pages**.
3. Under **Zone Resources**, select **All zones** (or your specific account).
4. Click **Continue to summary → Create Token**.
5. Copy the token immediately → this is your `CF_API_TOKEN`.

### 2d. Create the Pages project (one-time)

Run this once from your terminal (replace the values):

```bash
curl -X POST "https://api.cloudflare.com/client/v4/accounts/YOUR_CF_ACCOUNT_ID/pages/projects" \
  -H "Authorization: Bearer YOUR_CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"name":"sitesnap-sites","production_branch":"main"}'
```

Or use `cloudflare-deploy.js` in this repo:

```js
// Node.js (run once)
const { createCloudflarePagesProject } = require('./cloudflare-deploy.js');
createCloudflarePagesProject(
  'YOUR_CF_ACCOUNT_ID',
  'YOUR_CF_API_TOKEN',
  'sitesnap-sites'
).then(console.log);
```

A successful response includes `"subdomain": "sitesnap-sites.pages.dev"`.
Set `CF_PROJECT_NAME=sitesnap-sites` in n8n.

> **Note:** Each generated site is deployed as a new deployment under this one project.
> Each deployment gets its own unique hash URL (e.g. `https://abc123.sitesnap-sites.pages.dev`).
> That hash URL is what gets emailed to the client.

---

## 3. Anthropic API Setup

1. Sign in at [console.anthropic.com](https://console.anthropic.com).
2. Go to **Settings → API Keys → Create Key**.
3. Copy the key → `ANTHROPIC_API_KEY`.
4. The workflow uses **claude-opus-4-6** with a max of 8,000 output tokens.
   Ensure your account has sufficient credits. A typical site generation costs ~$0.05–$0.20.

---

## 4. Gmail Setup (n8n OAuth2 credential)

1. In n8n, go to **Settings → Credentials → Add Credential → Gmail OAuth2**.
2. Follow the OAuth2 flow to connect your Google account.
3. Grant the **Send email** scope.
4. Name the credential exactly **`Gmail account`** (must match the workflow JSON).
5. For admin alert emails to a different address, set `ADMIN_EMAIL` in n8n env vars.

> If you prefer an App Password instead of OAuth2:
> 1. Enable 2-Step Verification on your Google account.
> 2. Go to **Google Account → Security → App Passwords**.
> 3. Generate a password for "Mail" on "Windows Computer".
> 4. In n8n, create a **SMTP** credential instead of Gmail OAuth2, and update the
>    Send Email node type from `n8n-nodes-base.gmail` to `n8n-nodes-base.emailSend`.

---

## 5. n8n Setup

### 5a. Set environment variables

In your n8n Cloud instance (`capisoftnl.app.n8n.cloud`):

1. Go to **Settings → Environment Variables**.
2. Add each variable from `.env.example`:

| Variable | Value |
|---|---|
| `AIRTABLE_API_KEY` | Your Airtable personal access token |
| `AIRTABLE_BASE_ID` | e.g. `appXXXXXXXXXXXXXX` |
| `ANTHROPIC_API_KEY` | e.g. `sk-ant-api03-...` |
| `CF_API_TOKEN` | Your Cloudflare API token |
| `CF_ACCOUNT_ID` | Your Cloudflare account ID |
| `CF_PROJECT_NAME` | `sitesnap-sites` (or whatever you named it) |
| `ADMIN_EMAIL` | Your admin email address |

### 5b. Create the Webhook credential

1. Go to **Credentials → Add Credential → Header Auth**.
2. **Name**: `SiteSnap Webhook Key`
3. **Name** (field): `x-sitesnap-key`
4. **Value**: a long random secret, e.g. output of `openssl rand -hex 32`
5. Save it. Copy the secret value → you'll paste it into Lovable.

### 5c. Import the workflow

1. In n8n, go to **Workflows → Import from file**.
2. Select `n8n-workflow.json` from this repo.
3. The workflow imports as inactive.

### 5d. Connect credentials inside the workflow

Open the imported workflow and connect credentials to nodes that need them:

| Node | Credential needed |
|---|---|
| Webhook | SiteSnap Webhook Key (Header Auth) |
| Send Email | Gmail account (Gmail OAuth2) |
| Send Admin Alert | Gmail account (Gmail OAuth2) |

The Airtable and Claude API calls use environment variables directly — no separate n8n credential needed.

### 5e. Configure the error workflow

1. Open the workflow settings (gear icon).
2. Under **Error Workflow**, select **SiteSnap — Website Generator** (the same workflow).
3. This makes the **Error Trigger** node fire whenever any node in this workflow fails.

### 5f. Activate the workflow

Toggle the workflow from **Inactive → Active**.

### 5g. Copy the webhook URL

1. Click on the **Webhook** node.
2. Copy the **Production URL** — it looks like:
   `https://capisoftnl.app.n8n.cloud/webhook/sitesnap-generate`
3. Keep this URL; you'll paste it into Lovable next.

> **n8n Cloud execution timeout**: The default timeout on n8n Cloud's Starter plan is
> 5 minutes. Claude can occasionally take 60–90 seconds; the full workflow typically
> completes in 2–3 minutes. If you hit timeouts, upgrade to n8n Cloud's Pro plan
> (10-minute timeout) or switch to self-hosted n8n.

---

## 6. Connecting Lovable

In your Lovable project, find the form's submit handler. It should look something like:

```javascript
const handleSubmit = async (formData) => {
  const response = await fetch('YOUR_N8N_WEBHOOK_URL', {
    method: 'POST',
    headers: {
      'Content-Type':   'application/json',
      'x-sitesnap-key': 'YOUR_SITESNAP_WEBHOOK_SECRET',
    },
    body: JSON.stringify(formData),
  });

  const result = await response.json();
  if (result.success) {
    // Show success screen: "Check your email shortly!"
  }
};
```

Replace:
- `YOUR_N8N_WEBHOOK_URL` → the webhook Production URL from step 5g
- `YOUR_SITESNAP_WEBHOOK_SECRET` → the secret from the Header Auth credential (step 5b)

The webhook returns immediately with:
```json
{ "success": true, "message": "...", "requestId": "sr_..." }
```

Display a "We're generating your site — check your email in ~60 seconds!" message on success.

---

## 7. End-to-End Test

### What to send

Use this curl command (or Postman) to simulate a Lovable form submission:

```bash
curl -X POST https://capisoftnl.app.n8n.cloud/webhook/sitesnap-generate \
  -H "Content-Type: application/json" \
  -H "x-sitesnap-key: YOUR_SECRET_HERE" \
  -d '{
    "fullName":       "Test User",
    "email":          "your@email.com",
    "businessName":   "Test Business",
    "industry":       "Technology",
    "websiteType":    "Business Website",
    "pagesNeeded":    ["Home", "About", "Contact"],
    "designStyle":    "Clean & Minimal",
    "colorPreferences": "Blue and white",
    "tone":           "Professional",
    "tagline":        "Building the future",
    "services":       "Software consulting",
    "about":          "We help businesses grow with technology",
    "socialLinks":    "twitter.com/testbiz",
    "exampleSites":   "",
    "anythingElse":   "",
    "planSelected":   "Pro"
  }'
```

### Expected successful response

```json
{
  "success": true,
  "message": "Your website is being generated. You will receive an email shortly.",
  "requestId": "sr_1234567890_abc123"
}
```

### Verifying success

1. **n8n**: Open the execution log — all nodes should show green checkmarks.
2. **Airtable**: A new row appears in Website Requests with Status = "Live" and a URL in Generated Site URL.
3. **Cloudflare Pages**: Go to your Pages project dashboard — a new deployment appears.
4. **Email**: The address in `email` receives a "Your website is live!" email with a working link.

### Debugging failures

| Symptom | Check |
|---|---|
| Webhook returns 401 | `x-sitesnap-key` header doesn't match the credential value |
| Webhook returns 400 / "Missing required field" | `email`, `businessName`, or `websiteType` is empty in the payload |
| Airtable node fails | Check `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` env vars; verify field names match exactly |
| Claude node fails | Check `ANTHROPIC_API_KEY`; verify account has credits; check for rate limits |
| CF Pages node fails | Verify `CF_ACCOUNT_ID`, `CF_API_TOKEN`, `CF_PROJECT_NAME`; confirm project was created in step 2d |
| Email not received | Check Gmail credential is connected; check spam folder; verify `toList` expression in the node |
| Admin alert email not received | Check `ADMIN_EMAIL` env var; check Gmail credential |

For any node failure, click the execution in n8n and expand the failed node to see the raw error response from the API.

---

## File Reference

| File | Purpose |
|---|---|
| `n8n-workflow.json` | Import this into n8n |
| `airtable-helpers.js` | Reference / local testing for Airtable functions |
| `cloudflare-deploy.js` | Reference + one-time project setup script |
| `parse-claude-output.js` | Reference for the Claude output parser |
| `email-template.html` | Full HTML email template (used inline in the Gmail node) |
| `.env.example` | All required environment variables |
| `setup-guide.md` | This file |
