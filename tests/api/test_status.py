from fastapi.testclient import TestClient


def test_status_page_renders_for_any_job_id():
    from app.main import create_app

    c = TestClient(create_app())
    r = c.get("/status/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Building your site" in r.text
    assert "00000000-0000-0000-0000-000000000000" in r.text
