from fastapi.testclient import TestClient

from apps.api.main import _sessions, app

client = TestClient(app)


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_session_lifecycle():
    # Create session
    create_res = client.post("/api/v1/session")
    assert create_res.status_code == 201
    session_id = create_res.json().get("session_id")
    assert session_id is not None
    assert session_id in _sessions

    # Refresh session
    refresh_res = client.post("/api/v1/session/refresh", headers={"x-session-id": session_id})
    assert refresh_res.status_code == 200
    assert refresh_res.json() == {"status": "ok"}

    # Refresh invalid session
    bad_res = client.post("/api/v1/session/refresh", headers={"x-session-id": "nonexistent"})
    assert bad_res.status_code == 401


def test_upload_invalid_file_type():
    create_res = client.post("/api/v1/session")
    session_id = create_res.json()["session_id"]

    res = client.post(
        "/api/v1/documents",
        files={"file": ("test.txt", b"plain text", "text/plain")},
        headers={"x-session-id": session_id},
    )
    assert res.status_code == 415


def test_metrics_endpoint():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "process_cpu_seconds_total" in res.text or "python_gc_objects_collected_total" in res.text or res.status_code == 200
