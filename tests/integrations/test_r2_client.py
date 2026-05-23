from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.r2_client import R2Client


@pytest.fixture
def fake_s3_ctx():
    s3 = MagicMock()
    s3.put_object = AsyncMock(return_value={"ETag": '"abc"'})
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=s3)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx, s3


async def test_upload_one(fake_s3_ctx):
    ctx, s3 = fake_s3_ctx
    session = MagicMock()
    session.client = MagicMock(return_value=ctx)
    client = R2Client(session=session)

    await client.put(
        key="sites/x/index.html",
        body=b"<html></html>",
        content_type="text/html",
        cache_control="public, max-age=300",
    )
    s3.put_object.assert_called_once()
    args = s3.put_object.call_args.kwargs
    assert args["Key"] == "sites/x/index.html"
    assert args["ContentType"] == "text/html"
    assert args["CacheControl"] == "public, max-age=300"


async def test_put_many_uploads_in_parallel(fake_s3_ctx):
    ctx, s3 = fake_s3_ctx
    session = MagicMock()
    session.client = MagicMock(return_value=ctx)
    client = R2Client(session=session)

    items = [
        ("sites/x/index.html", b"a", "text/html", "public, max-age=300"),
        ("sites/x/styles.css", b"b", "text/css", "public, max-age=31536000, immutable"),
    ]
    await client.put_many(items)
    assert s3.put_object.await_count == 2
