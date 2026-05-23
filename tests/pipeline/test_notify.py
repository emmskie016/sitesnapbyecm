from unittest.mock import AsyncMock

import pytest

from app.pipeline.notify import notify_customer_and_operator


@pytest.fixture
def fake_resend():
    r = AsyncMock()
    r.send = AsyncMock(return_value="msg_c")
    r.send_operator = AsyncMock(return_value="msg_o")
    return r


async def test_notify_sends_both_emails(fake_resend):
    await notify_customer_and_operator(
        resend=fake_resend,
        customer_email="c@example.com",
        customer_name="Jane",
        brand_name="Bloom",
        site_url="https://bloom-x7k2.sitesnap.app",
        archetype="service",
        tokens_in=300,
        tokens_out=400,
        cost_usd=0.012,
        slug="bloom-x7k2",
    )
    fake_resend.send.assert_awaited_once()
    fake_resend.send_operator.assert_awaited_once()
    cust_args = fake_resend.send.await_args.kwargs
    assert cust_args["to"] == "c@example.com"
    assert "bloom-x7k2" in cust_args["html"]
    op_args = fake_resend.send_operator.await_args.kwargs
    assert "$0.0120" in op_args["html"] or "0.012" in op_args["html"]
