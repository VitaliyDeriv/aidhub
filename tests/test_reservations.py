import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Reservation


def reserve(client, headers, ids):
    return client.post("/api/v1/reservations", json={"pallet_ids": ids}, headers=headers)


def pallet_statuses(client, headers):
    response = client.get("/api/v1/pallets", headers=headers)
    return {p["id"]: p["status"] for p in response.json()}


def test_reserve_marks_pallets_reserved(client, user_a, pallet_ids):
    response = reserve(client, user_a["headers"], pallet_ids[:2])
    assert response.status_code == 201
    assert {r["pallet_id"] for r in response.json()} == set(pallet_ids[:2])
    statuses = pallet_statuses(client, user_a["headers"])
    assert statuses[pallet_ids[0]] == "reserved"
    assert statuses[pallet_ids[2]] == "available"


def test_double_booking_same_pallet_is_rejected(client, user_a, user_b, pallet_ids):
    assert reserve(client, user_a["headers"], pallet_ids[:1]).status_code == 201
    second = reserve(client, user_b["headers"], pallet_ids[:1])
    assert second.status_code == 409
    # той самий фонд теж не може забронювати двічі
    assert reserve(client, user_a["headers"], pallet_ids[:1]).status_code == 409


def test_reservation_request_is_atomic(client, user_a, user_b, pallet_ids):
    assert reserve(client, user_a["headers"], [pallet_ids[1]]).status_code == 201
    response = reserve(client, user_b["headers"], [pallet_ids[0], pallet_ids[1]])
    assert response.status_code == 409
    # вільна палета з невдалого запиту не повинна «прилипнути»
    assert pallet_statuses(client, user_b["headers"])[pallet_ids[0]] == "available"
    assert client.get("/api/v1/reservations", headers=user_b["headers"]).json() == []


def test_duplicate_ids_in_request_are_deduplicated(client, user_a, pallet_ids):
    response = reserve(client, user_a["headers"], [pallet_ids[0], pallet_ids[0]])
    assert response.status_code == 201
    assert len(response.json()) == 1


def test_unknown_pallet_returns_404(client, user_a, pallet_ids):
    assert reserve(client, user_a["headers"], [pallet_ids[0], 99999]).status_code == 404
    assert pallet_statuses(client, user_a["headers"])[pallet_ids[0]] == "available"


def test_empty_request_is_rejected(client, user_a):
    assert reserve(client, user_a["headers"], []).status_code == 422


def test_admin_without_fund_cannot_reserve(client, admin_headers, pallet_ids):
    assert reserve(client, admin_headers, pallet_ids[:1]).status_code == 403


def test_cancel_frees_pallet_for_other_fund(client, user_a, user_b, pallet_ids):
    created = reserve(client, user_a["headers"], pallet_ids[:1]).json()[0]
    cancelled = client.delete(f"/api/v1/reservations/{created['id']}", headers=user_a["headers"])
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert pallet_statuses(client, user_a["headers"])[pallet_ids[0]] == "available"
    assert reserve(client, user_b["headers"], pallet_ids[:1]).status_code == 201


def test_cancel_twice_conflicts(client, user_a, pallet_ids):
    created = reserve(client, user_a["headers"], pallet_ids[:1]).json()[0]
    path = f"/api/v1/reservations/{created['id']}"
    assert client.delete(path, headers=user_a["headers"]).status_code == 200
    assert client.delete(path, headers=user_a["headers"]).status_code == 409


def test_admin_sees_all_reservations_and_stats(client, admin_headers, user_a, user_b, pallet_ids):
    reserve(client, user_a["headers"], pallet_ids[:1])
    reserve(client, user_b["headers"], pallet_ids[1:2])
    assert len(client.get("/api/v1/reservations", headers=admin_headers).json()) == 2
    stats = client.get("/api/v1/admin/stats", headers=admin_headers).json()
    assert stats["pallets_total"] == 4
    assert stats["pallets_reserved"] == 2
    assert stats["pallets_available"] == 2
    assert stats["active_reservations"] == 2


def test_database_blocks_two_active_reservations_for_one_pallet(client, user_a, pallet_ids):
    """Другий рівень захисту: обмеження в БД спрацьовує, навіть якщо обійти сервіс."""
    created = reserve(client, user_a["headers"], pallet_ids[:1]).json()[0]
    with Session(engine) as db:
        db.add(Reservation(pallet_id=pallet_ids[0], fund_id=created["fund_id"], user_id=1))
        with pytest.raises(IntegrityError):
            db.commit()
