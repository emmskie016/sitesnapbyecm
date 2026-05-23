from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
from loguru import logger

from app.settings import settings


class DB:
    def __init__(self) -> None:
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                settings.supabase_db_url,
                min_size=1,
                max_size=10,
                command_timeout=30,
            )
            logger.info("db pool connected")

    async def disconnect(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def insert_submission(
        self,
        *,
        full_name: str,
        email: str,
        brand_name: str,
        industry: str,
        questionnaire: dict[str, Any],
        ip: str | None,
        user_agent: str | None,
        request_hash: str,
    ) -> UUID:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            """
            insert into submissions
            (full_name, email, brand_name, industry, questionnaire, ip,
             user_agent, request_hash)
            values ($1, $2, $3, $4, $5::jsonb, $6::inet, $7, $8)
            on conflict (request_hash) do update set
            request_hash = excluded.request_hash
            returning id
            """,
            full_name,
            email,
            brand_name,
            industry,
            json.dumps(questionnaire),
            ip,
            user_agent,
            request_hash,
        )
        return row["id"]

    async def insert_job(self, submission_id: UUID) -> UUID:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            "insert into jobs (submission_id) values ($1) returning id",
            submission_id,
        )
        return row["id"]

    async def fetch_job(self, job_id: UUID) -> dict[str, Any] | None:
        assert self.pool is not None
        row = await self.pool.fetchrow("select * from jobs where id = $1", job_id)
        return dict(row) if row else None

    async def fetch_submission(self, submission_id: UUID) -> dict[str, Any] | None:
        assert self.pool is not None
        row = await self.pool.fetchrow("select * from submissions where id = $1", submission_id)
        return dict(row) if row else None

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        *,
        progress_pct: int | None = None,
        archetype: str | None = None,
        slug: str | None = None,
        palette: dict | None = None,
        site_url: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        started_at_now: bool = False,
        finished_at_now: bool = False,
    ) -> None:
        assert self.pool is not None
        sets = ["status = $2"]
        params: list[Any] = [job_id, status]

        def add(field: str, value: Any) -> None:
            params.append(value)
            sets.append(f"{field} = ${len(params)}")

        if progress_pct is not None:
            add("progress_pct", progress_pct)
        if archetype is not None:
            add("archetype", archetype)
        if slug is not None:
            add("slug", slug)
        if palette is not None:
            add("palette", json.dumps(palette))
            sets[-1] = f"palette = ${len(params)}::jsonb"
        if site_url is not None:
            add("site_url", site_url)
        if error_code is not None:
            add("error_code", error_code)
        if error_message is not None:
            add("error_message", error_message)
        if started_at_now:
            sets.append("started_at = coalesce(started_at, now())")
        if finished_at_now:
            sets.append("finished_at = now()")

        await self.pool.execute(
            f"update jobs set {', '.join(sets)} where id = $1",
            *params,
        )

    async def increment_attempts(self, job_id: UUID) -> int:
        assert self.pool is not None
        row = await self.pool.fetchrow(
            "update jobs set attempts = attempts + 1 where id = $1 returning attempts",
            job_id,
        )
        return row["attempts"]

    async def slug_exists(self, slug: str, *, exclude_job_id: UUID | None = None) -> bool:
        assert self.pool is not None
        if exclude_job_id is not None:
            row = await self.pool.fetchval(
                "select 1 from jobs where slug = $1 and id <> $2 limit 1",
                slug,
                exclude_job_id,
            )
        else:
            row = await self.pool.fetchval(
                "select 1 from jobs where slug = $1 limit 1",
                slug,
            )
        return row is not None

    async def add_claude_usage(
        self, job_id: UUID, *, tokens_in: int, tokens_out: int, cost_usd: float
    ) -> None:
        assert self.pool is not None
        await self.pool.execute(
            """
            update jobs
            set claude_tokens_in = claude_tokens_in + $2,
                claude_tokens_out = claude_tokens_out + $3,
                claude_cost_usd = claude_cost_usd + $4
            where id = $1
            """,
            job_id,
            tokens_in,
            tokens_out,
            cost_usd,
        )


db = DB()
