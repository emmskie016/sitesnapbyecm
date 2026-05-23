import pytest

from app.db import DB


@pytest.mark.skipif("not __import__('os').environ.get('RUN_DB_TESTS')", reason="requires live DB")
async def test_db_roundtrip():
    db = DB()
    await db.connect()
    try:
        sub_id = await db.insert_submission(
            full_name="Test",
            email="t@example.com",
            brand_name="TestCo",
            industry="tech",
            questionnaire={"a": 1},
            ip=None,
            user_agent="test",
            request_hash="hash-1",
        )
        assert sub_id

        job_id = await db.insert_job(sub_id)
        row = await db.fetch_job(job_id)
        assert row["status"] == "queued"

        await db.update_job_status(job_id, "classifying", progress_pct=10)
        row = await db.fetch_job(job_id)
        assert row["status"] == "classifying"
        assert row["progress_pct"] == 10
    finally:
        await db.disconnect()


def test_db_constructible_without_connect():
    db = DB()
    assert db.pool is None
