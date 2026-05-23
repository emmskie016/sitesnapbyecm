from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from app.main import create_app

    fake_db = AsyncMock()
    fake_db.fetch_job = AsyncMock(return_value={"id": "abc", "status": "failed", "submission_id": "sub1"})
    fake_db.update_job_status = AsyncMock()
    monkeypatch.setattr("app.api.admin.db", fake_db)

    c = TestClient(create_app())
    return c, fake_db


def test_admin_retry_requires_bearer_token(client):
    c, _ = client
    r = c.post("/api/admin/jobs/00000000-0000-0000-0000-000000000000/retry")
    assert r.status_code == 401


def test_admin_retry_rejects_wrong_token(client):
    c, _ = client
    r = c.post(
        "/api/admin/jobs/00000000-0000-0000-0000-000000000000/retry",
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401


def test_admin_retry_accepts_correct_token_and_requeues(client):
    c, fake_db = client
    r = c.post(
        "/api/admin/jobs/00000000-0000-0000-0000-000000000000/retry",
        headers={"Authorization": "Bearer test-admin"},
    )
    assert r.status_code == 202
    fake_db.update_job_status.assert_awaited()
