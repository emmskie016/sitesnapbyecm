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
        customer_name=customer_name,
        brand_name=brand_name,
        site_url=site_url,
    )
    op_html = OPERATOR_HTML.format(
        brand_name=brand_name,
        slug=slug,
        site_url=site_url,
        archetype=archetype,
        customer_name=customer_name,
        customer_email=customer_email,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
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
