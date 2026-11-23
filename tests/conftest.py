import os

# Змінні задаються ДО імпорту застосунку: тести завжди працюють на in-memory SQLite
# і ніколи не торкаються sandbox/production баз.
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789abcdef"
os.environ["ADMIN_EMAIL"] = "admin@example.org"
os.environ["ADMIN_PASSWORD"] = "admin-password-1"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

ADMIN_EMAIL = "admin@example.org"
ADMIN_PASSWORD = "admin-password-1"
USER_PASSWORD = "user-password-1"


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client(_fresh_db):
    # Виконання lifespan створює адміністратора з ADMIN_EMAIL / ADMIN_PASSWORD.
    with TestClient(app) as test_client:
        yield test_client


def login_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    client.cookies.clear()  # щоб cookie не робила наступні запити "авторизованими"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_user(client: TestClient, email: str, fund_name: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": USER_PASSWORD,
            "full_name": f"User {email}",
            "fund_name": fund_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def admin_headers(client):
    return login_headers(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def user_a(client):
    data = register_user(client, "a@example.org", "Fund A")
    return {"user": data, "headers": login_headers(client, "a@example.org", USER_PASSWORD)}


@pytest.fixture
def user_b(client):
    data = register_user(client, "b@example.org", "Fund B")
    return {"user": data, "headers": login_headers(client, "b@example.org", USER_PASSWORD)}


@pytest.fixture
def pallet_ids(client, admin_headers):
    warehouse = client.post(
        "/api/v1/admin/warehouses",
        json={"name": "Central", "city": "Lviv"},
        headers=admin_headers,
    )
    assert warehouse.status_code == 201
    response = client.post(
        "/api/v1/admin/pallets",
        json={
            "warehouse_id": warehouse.json()["id"],
            "description": "Water 1.5L",
            "units": 600,
            "count": 4,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    return [p["id"] for p in response.json()]
