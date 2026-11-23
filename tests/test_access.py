"""Вертикальне (ролі) та горизонтальне (IDOR) розмежування прав."""

# ---- Вертикальне розмежування -------------------------------------------------


def test_user_forbidden_on_admin_endpoints(client, user_a):
    for path in ("/api/v1/admin/users", "/api/v1/admin/stats"):
        assert client.get(path, headers=user_a["headers"]).status_code == 403
    response = client.post(
        "/api/v1/admin/warehouses",
        json={"name": "X", "city": "Y"},
        headers=user_a["headers"],
    )
    assert response.status_code == 403


def test_user_forbidden_on_admin_home(client, user_a):
    assert client.get("/home/admin", headers=user_a["headers"]).status_code == 403


def test_admin_allowed_on_admin_endpoints(client, admin_headers, user_a):
    users = client.get("/api/v1/admin/users", headers=admin_headers)
    assert users.status_code == 200
    assert {u["email"] for u in users.json()} == {"admin@example.org", "a@example.org"}
    assert client.get("/api/v1/admin/stats", headers=admin_headers).status_code == 200
    assert client.get("/home/admin", headers=admin_headers).status_code == 200


def test_admin_forbidden_on_user_home(client, admin_headers):
    assert client.get("/home/user", headers=admin_headers).status_code == 403


def test_home_pages_for_each_role(client, user_a, admin_headers):
    page = client.get("/home/user", headers=user_a["headers"])
    assert page.status_code == 200
    assert "Кабінет фонду" in page.text
    redirect = client.get("/home", headers=user_a["headers"], follow_redirects=False)
    assert redirect.headers["location"] == "/home/user"
    redirect = client.get("/home", headers=admin_headers, follow_redirects=False)
    assert redirect.headers["location"] == "/home/admin"


def test_home_page_escapes_user_name(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "xss@example.org",
            "password": "user-password-1",
            "full_name": "<script>alert(1)</script>",
            "fund_name": "XSS Fund",
        },
    )
    login = client.post(
        "/api/v1/auth/login", data={"username": "xss@example.org", "password": "user-password-1"}
    )
    page = client.get(
        "/home/user", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    assert "<script>alert(1)</script>" not in page.text


# ---- Горизонтальне розмежування (IDOR) ---------------------------------------


def test_user_cannot_read_other_profile(client, user_a, user_b):
    response = client.get(f"/api/v1/users/{user_b['user']['id']}", headers=user_a["headers"])
    assert response.status_code == 403


def test_user_cannot_modify_other_profile(client, user_a, user_b):
    response = client.patch(
        f"/api/v1/users/{user_b['user']['id']}",
        json={"full_name": "Hacked"},
        headers=user_a["headers"],
    )
    assert response.status_code == 403
    me_b = client.get("/api/v1/users/me", headers=user_b["headers"]).json()
    assert me_b["full_name"] != "Hacked"


def test_user_does_not_learn_whether_id_exists(client, user_a):
    assert client.get("/api/v1/users/99999", headers=user_a["headers"]).status_code == 403


def test_user_can_modify_own_profile(client, user_a):
    response = client.patch(
        f"/api/v1/users/{user_a['user']['id']}",
        json={"full_name": "Renamed"},
        headers=user_a["headers"],
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed"
    assert response.json()["role"] == "user"


def test_profile_update_cannot_change_role(client, user_a):
    client.patch(
        f"/api/v1/users/{user_a['user']['id']}",
        json={"role": "admin", "fund_id": 1},
        headers=user_a["headers"],
    )
    assert client.get("/api/v1/users/me", headers=user_a["headers"]).json()["role"] == "user"


def test_admin_can_modify_any_profile(client, admin_headers, user_a):
    response = client.patch(
        f"/api/v1/users/{user_a['user']['id']}",
        json={"full_name": "Set by admin"},
        headers=admin_headers,
    )
    assert response.status_code == 200


def test_user_cannot_access_foreign_reservation(client, user_a, user_b, pallet_ids):
    created = client.post(
        "/api/v1/reservations", json={"pallet_ids": pallet_ids[:1]}, headers=user_a["headers"]
    )
    assert created.status_code == 201
    reservation_id = created.json()[0]["id"]

    assert (
        client.get(f"/api/v1/reservations/{reservation_id}", headers=user_b["headers"]).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/reservations/{reservation_id}", headers=user_b["headers"]
        ).status_code
        == 403
    )
    # чужа бронь лишилась активною
    assert (
        client.get(f"/api/v1/reservations/{reservation_id}", headers=user_a["headers"]).json()[
            "status"
        ]
        == "active"
    )
    assert client.get("/api/v1/reservations", headers=user_b["headers"]).json() == []
