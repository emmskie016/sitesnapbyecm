from __future__ import annotations

import asyncio

import resend

from app.settings import settings

resend.api_key = settings.resend_api_key


class ResendClient:
    async def send(self, *, to: str, subject: str, html: str) -> str:
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
