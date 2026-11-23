from fastapi.testclient import TestClient

from app.main import app
from app.security import hash_password, verify_password


def test_password_hash_is_salted_and_verifiable():
    first, second = hash_password("correct horse"), hash_password("correct horse")
    assert first != second
    assert verify_password("correct horse", first)
    assert not verify_password("wrong", first)
    assert not verify_password("anything", "garbage")


def test_unhandled_error_does_not_leak_internals(client):
    def boom():
        raise RuntimeError("secret internal detail")

    app.add_api_route("/__boom", boom)
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get("/__boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text


def test_docs_are_disabled_when_debug_is_off(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_response_identifies_instance(client):
    response = client.get("/health")
    assert response.headers["X-Instance"]
    assert response.json()["instance"] == response.headers["X-Instance"]
