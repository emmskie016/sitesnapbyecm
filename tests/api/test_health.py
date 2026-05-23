from fastapi.testclient import TestClient


def test_healthz_returns_ok_status_and_dependency_map():
    from app.main import create_app
    c = TestClient(create_app())
    r = c.get("/healthz")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] in ("ok", "degraded")
    assert "dependencies" in j
    assert set(j["dependencies"].keys()) >= {"claude", "supabase", "r2", "unsplash", "resend"}
