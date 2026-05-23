from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

import aioboto3

from app.settings import settings


class R2Client:
    def __init__(self, session: Any | None = None) -> None:
        self.session = session or aioboto3.Session()
        self.endpoint = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"

    def _client(self):
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )

    async def put(
        self,
        *,
        key: str,
        body: bytes,
        content_type: str,
        cache_control: str,
    ) -> None:
        async with self._client() as s3:
            await s3.put_object(
                Bucket=settings.r2_bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                CacheControl=cache_control,
            )

    async def put_many(self, items: Iterable[tuple[str, bytes, str, str]]) -> None:
        items_list = list(items)
        async with self._client() as s3:
            await asyncio.gather(
                *[
                    s3.put_object(
                        Bucket=settings.r2_bucket,
                        Key=key,
                        Body=body,
                        ContentType=content_type,
                        CacheControl=cache_control,
                    )
                    for (key, body, content_type, cache_control) in items_list
                ]
            )


r2 = R2Client()
