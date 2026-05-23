from unittest.mock import MagicMock, patch

from app.integrations.resend_client import ResendClient


async def test_send_customer_email_calls_sdk():
    with patch(
        "app.integrations.resend_client.resend.Emails.send",
        new=MagicMock(return_value={"id": "msg_1"}),
    ) as send:
        client = ResendClient()
        msg_id = await client.send(
            to="customer@example.com",
            subject="Your site is live",
            html="<p>hi</p>",
        )
        assert msg_id == "msg_1"
        assert send.call_args.args[0]["to"] == ["customer@example.com"]


async def test_send_operator_email_uses_operator_address():
    with patch(
        "app.integrations.resend_client.resend.Emails.send",
        new=MagicMock(return_value={"id": "msg_2"}),
    ) as send:
        client = ResendClient()
        await client.send_operator(subject="New site", html="<p>done</p>")
        to_addr = send.call_args.args[0]["to"][0]
        assert to_addr.endswith("@sitesnap.app") or to_addr == "ops@sitesnap.app"
