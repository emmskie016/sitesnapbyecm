from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    from app.main import create_app

    fake_db = AsyncMock()
    fake_db.insert_submission = AsyncMock(return_value=uuid4())
    fake_db.insert_job = AsyncMock(return_value=uuid4())
    fake_db.fetch_job = AsyncMock(return_value={
        "id": "00000000-0000-0000-0000-000000000000",
        "status": "writing_copy", "progress_pct": 30,
        "site_url": None, "error_code": None, "error_message": None,
    })

    monkeypatch.setattr("app.api.sites.db", fake_db)
    app = create_app()
    return TestClient(app), fake_db


def test_post_sites_returns_202_and_status_url(client):
    c, _ = client
    payload = {
        "full_name": "Jane Doe", "email": "jane@example.com",
        "brand_name": "Bloom", "industry": "florist",
        "questionnaire": {"tone": "warm"},
    }
    r = c.post("/api/sites", json=payload)
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body
    assert body["status_url"].startswith("/status/")


def test_post_sites_rejects_bad_email(client):
    c, _ = client
    r = c.post("/api/sites", json={
        "full_name": "x", "email": "nope", "brand_name": "x", "industry": "x",
    })
    assert r.status_code == 422


def test_get_job_returns_status(client):
    c, _ = client
    r = c.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "writing_copy"
    assert j["progress_pct"] == 30


def test_get_unknown_job_404(client):
    c, fake_db = client
    fake_db.fetch_job = AsyncMock(return_value=None)
    r = c.get("/api/jobs/11111111-1111-1111-1111-111111111111")
    assert r.status_code == 404
