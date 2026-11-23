"""Сценарій навантаження: типова поведінка фонду.

Запуск (веб-інтерфейс):
    locust -f loadtests/locustfile.py --host http://localhost:8000
Headless із профілем з docs/load-testing.md:
    locust -f loadtests/locustfile.py --host http://localhost:8000 --headless \
        -u 50 -r 5 -t 3m --csv loadtests/results/run1 --html loadtests/results/run1.html

Змінні: ADMIN_EMAIL / ADMIN_PASSWORD — для підготовки складу (створення палет).
"""

import os
import random
import uuid

from locust import HttpUser, between, events, task

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.org")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
PALLETS_PER_RUN = int(os.getenv("PALLETS_PER_RUN", "5000"))

pallet_pool: list[int] = []


@events.test_start.add_listener
def seed_pallets(environment, **_):
    """Адміністратор створює склад і палети, які фонди змагатимуться бронювати."""
    import requests

    host = environment.host
    token = requests.post(
        f"{host}/api/v1/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10,
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    warehouse = requests.post(
        f"{host}/api/v1/admin/warehouses",
        json={"name": f"LT-{uuid.uuid4().hex[:6]}", "city": "Load"},
        headers=headers,
        timeout=10,
    ).json()
    for _ in range(PALLETS_PER_RUN // 500):
        created = requests.post(
            f"{host}/api/v1/admin/pallets",
            json={
                "warehouse_id": warehouse["id"],
                "description": "Load test pallet",
                "units": 100,
                "count": 500,
            },
            headers=headers,
            timeout=30,
        ).json()
        pallet_pool.extend(p["id"] for p in created)


class FundUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.email = f"lt-{uuid.uuid4().hex[:10]}@example.org"
        password = "load-test-pass-1"
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": password,
                "full_name": "Load User",
                "fund_name": f"Fund {uuid.uuid4().hex[:10]}",
            },
            name="/api/v1/auth/register",
        )
        response = self.client.post(
            "/api/v1/auth/login",
            data={"username": self.email, "password": password},
            name="/api/v1/auth/login",
        )
        token = response.json().get("access_token", "")
        self.client.headers["Authorization"] = f"Bearer {token}"
        self.my_reservations: list[int] = []

    @task(1)
    def landing(self):
        self.client.get("/", name="GET /")

    @task(5)
    def browse_pallets(self):
        self.client.get("/api/v1/pallets?status=available&limit=50", name="GET /pallets")

    @task(3)
    def reserve_contended(self):
        """Усі віртуальні користувачі б'ються за один малий діапазон палет —
        це й створює конкуренцію за блокування рядків."""
        if not pallet_pool:
            return
        hot = pallet_pool[:200]
        ids = random.sample(hot, k=min(3, len(hot)))
        with self.client.post(
            "/api/v1/reservations",
            json={"pallet_ids": ids},
            name="POST /reservations (hot)",
            catch_response=True,
        ) as response:
            if response.status_code == 409:
                response.success()  # очікувана відмова: палета вже заброньована
            elif response.status_code == 201:
                self.my_reservations.extend(r["id"] for r in response.json())

    @task(2)
    def reserve_free(self):
        """Бронювання з широкого пулу — майже без конфліктів."""
        if len(pallet_pool) <= 200:
            return
        pallet = random.choice(pallet_pool[200:])
        with self.client.post(
            "/api/v1/reservations",
            json={"pallet_ids": [pallet]},
            name="POST /reservations (cold)",
            catch_response=True,
        ) as response:
            if response.status_code == 409:
                response.success()

    @task(2)
    def my_list(self):
        self.client.get("/api/v1/reservations", name="GET /reservations")

    @task(1)
    def cancel_one(self):
        if self.my_reservations:
            rid = self.my_reservations.pop()
            self.client.delete(f"/api/v1/reservations/{rid}", name="DELETE /reservations/{id}")
