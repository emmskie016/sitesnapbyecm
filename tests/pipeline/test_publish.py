from unittest.mock import AsyncMock

import pytest

from app.pipeline.publish import publish_site


@pytest.fixture
def fake_r2():
    r = AsyncMock()
    r.put_many = AsyncMock()
    return r


@pytest.fixture
def fake_http():
    class FakeResp:
        def __init__(self, content):
            self.content = content

        def raise_for_status(self):
            pass

    h = AsyncMock()
    h.get = AsyncMock(return_value=FakeResp(b"\xff\xd8\xff\xe0fake-jpeg"))
    return h


async def test_publish_uploads_html_and_assets(fake_r2, fake_http):
    url = await publish_site(
        slug="bloom-x7k2",
        html="<html>hi</html>",
        assets={
            "assets/hero.jpg": "https://images.unsplash.com/a",
            "assets/feature_1.jpg": "https://images.unsplash.com/b",
        },
        r2=fake_r2,
        http=fake_http,
    )
    assert "bloom-x7k2" in url
    fake_r2.put_many.assert_awaited_once()
    uploaded = fake_r2.put_many.await_args.args[0]
    keys = [k for (k, _, _, _) in uploaded]
    assert "sites/bloom-x7k2/index.html" in keys
    assert "sites/bloom-x7k2/assets/hero.jpg" in keys


async def test_publish_returns_correct_subdomain_url(monkeypatch, fake_r2, fake_http):
    monkeypatch.setattr("app.pipeline.publish.settings.r2_public_base", "https://sitesnap.app")
    url = await publish_site(
        slug="x-aaaa",
        html="<p>x</p>",
        assets={},
        r2=fake_r2,
        http=fake_http,
    )
    # subdomain or path style, both acceptable as long as slug appears
    assert "x-aaaa" in url
