from __future__ import annotations

from app.integrations.resend_client import ResendClient
from app.settings import settings

CUSTOMER_HTML = """\
<!doctype html>
<html><body style="font-family: -apple-system, system-ui, sans-serif; background:#FAF6F1; padding:32px;">
  <div style="max-width:560px; margin:0 auto; background:#fff; border-radius:16px; padding:40px; box-shadow:0 8px 32px rgba(0,0,0,.06);">
    <div style="display:inline-block; padding:5px 14px; background:#ECFDF5; color:#047857; border-radius:999px; font-size:13px; font-weight:600; letter-spacing:.02em; margin-bottom:16px;">Live now</div>
    <h1 style="margin:0 0 12px; font-size:26px; color:#0F172A; line-height:1.2;">Your {brand_name} website is live &#127881;</h1>
    <p style="margin:0 0 24px; color:#475569; line-height:1.6;">Hi {customer_name}, your custom site has been built and published. Tap the button to view it &mdash; the link is yours to share with anyone.</p>
    <p style="margin:0 0 28px;"><a href="{site_url}" style="background:#1E293B; color:#fff; padding:14px 26px; border-radius:999px; text-decoration:none; display:inline-block; font-weight:600;">Visit your site &rarr;</a></p>
    <p style="margin:0 0 8px; font-size:13px; color:#94A3B8;">Direct link:</p>
    <p style="margin:0 0 28px; font-size:14px; word-break:break-all;"><a href="{site_url}" style="color:#1E3A8A;">{site_url}</a></p>
    <hr style="border:none; border-top:1px solid #E2E8F0; margin:0 0 24px;">
    <h2 style="margin:0 0 8px; font-size:17px; color:#0F172A;">Need changes or extra features?</h2>
    <p style="margin:0 0 16px; font-size:14px; color:#475569; line-height:1.6;">This is just v1. If you want edits, additional pages, new sections, custom branding, or anything we missed &mdash; just reply to this email or write to us directly.</p>
    <p style="margin:0 0 24px; font-size:14px;"><a href="mailto:{contact_email}?subject=SiteSnap%20edit%20request%20for%20{brand_name_url}" style="display:inline-block; padding:10px 18px; border:1px solid #CBD5E1; border-radius:999px; color:#1E293B; text-decoration:none; font-weight:500;">Email {contact_email}</a></p>
    <hr style="border:none; border-top:1px solid #E2E8F0; margin:0 0 16px;">
    <p style="margin:0; font-size:12px; color:#94A3B8;">Built with SiteSnap.</p>
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
    from urllib.parse import quote

    cust_html = CUSTOMER_HTML.format(
        customer_name=customer_name,
        brand_name=brand_name,
        brand_name_url=quote(brand_name),
        site_url=site_url,
        contact_email=settings.resend_operator_email,
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
