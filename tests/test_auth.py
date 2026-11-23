import pytest

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, register_user

PROTECTED = [
    "/api/v1/users/me",
    "/api/v1/pallets",
    "/api/v1/warehouses",
    "/api/v1/reservations",
    "/api/v1/admin/users",
    "/api/v1/admin/stats",
    "/home/user",
    "/home/admin",
]


@pytest.mark.parametrize("path", PROTECTED)
def test_anonymous_gets_401(client, path):
    response = client.get(path)
    assert response.status_code == 401


def test_anonymous_home_redirects_to_landing(client):
    response = client.get("/home", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/"


def test_invalid_token_gets_401(client):
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_register_creates_regular_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "New@Example.org ",
            "password": USER_PASSWORD,
            "full_name": "New User",
            "fund_name": "New Fund",
            "role": "admin",  # спроба підняти собі роль має ігноруватися
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "user"
    assert body["email"] == "new@example.org"
    assert body["fund_id"] is not None
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_conflicts(client):
    register_user(client, "dup@example.org", "Fund One")
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.org",
            "password": USER_PASSWORD,
            "full_name": "Other",
            "fund_name": "Fund Two",
        },
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.org", "password": "short", "full_name": "X", "fund_name": "X"},
    )
    assert response.status_code == 422


def test_login_success_returns_token_and_cookie(client, user_a):
    response = client.post(
        "/api/v1/auth/login", data={"username": "a@example.org", "password": USER_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert "access_token" in response.cookies
    # cookie, збережена клієнтом, автентифікує без заголовка
    assert client.get("/api/v1/users/me").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/users/me").status_code == 401


def test_admin_login_success(client):
    response = client.post(
        "/api/v1/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("a@example.org", "wrong-password"),
        ("nobody@example.org", USER_PASSWORD),
        ("", ""),
    ],
)
def test_login_failures(client, user_a, username, password):
    response = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert response.status_code in (401, 422)
    assert "access_token" not in response.json()


def test_valid_token_gives_access(client, user_a):
    response = client.get("/api/v1/users/me", headers=user_a["headers"])
    assert response.status_code == 200
    assert response.json()["email"] == "a@example.org"
