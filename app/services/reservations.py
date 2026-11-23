"""Транзакційне резервування палет.

Захист від подвійного бронювання має два рівні:
1. `SELECT ... FOR UPDATE` блокує рядки палет на час транзакції; палети
   завжди блокуються в порядку зростання id, тож взаємоблокувань
   між конкурентними запитами немає.
2. Часткове унікальне обмеження `uq_reservation_active_pallet` у БД не
   дозволяє створити другу активну бронь на ту саму палету навіть при
   помилці в коді застосунку.
Запит атомарний: або резервуються всі палети, або жодна.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Pallet, PalletStatus, Reservation, ReservationStatus, Role, User


class PalletsNotFound(Exception):
    def __init__(self, ids: list[int]):
        self.ids = ids


class PalletsUnavailable(Exception):
    def __init__(self, ids: list[int]):
        self.ids = ids


class NoFund(Exception):
    """Користувач не належить до фонду (наприклад, адміністратор)."""


class ReservationNotFound(Exception):
    pass


class ReservationForbidden(Exception):
    pass


class ReservationNotActive(Exception):
    pass


def reserve_pallets(db: Session, user: User, pallet_ids: list[int]) -> list[Reservation]:
    if user.fund_id is None:
        raise NoFund
    ids = sorted(set(pallet_ids))
    pallets = (
        db.execute(select(Pallet).where(Pallet.id.in_(ids)).order_by(Pallet.id).with_for_update())
        .scalars()
        .all()
    )
    missing = sorted(set(ids) - {p.id for p in pallets})
    if missing:
        db.rollback()
        raise PalletsNotFound(missing)
    busy = [p.id for p in pallets if p.status != PalletStatus.AVAILABLE]
    if busy:
        db.rollback()
        raise PalletsUnavailable(busy)

    reservations = []
    for pallet in pallets:
        pallet.status = PalletStatus.RESERVED.value
        reservation = Reservation(pallet_id=pallet.id, fund_id=user.fund_id, user_id=user.id)
        db.add(reservation)
        reservations.append(reservation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise PalletsUnavailable(ids) from None
    return reservations


def get_reservation(db: Session, user: User, reservation_id: int) -> Reservation:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise ReservationNotFound
    if user.role != Role.ADMIN and reservation.fund_id != user.fund_id:
        raise ReservationForbidden
    return reservation


def cancel_reservation(db: Session, user: User, reservation_id: int) -> Reservation:
    reservation = db.execute(
        select(Reservation).where(Reservation.id == reservation_id).with_for_update()
    ).scalar_one_or_none()
    if reservation is None:
        db.rollback()
        raise ReservationNotFound
    if user.role != Role.ADMIN and reservation.fund_id != user.fund_id:
        db.rollback()
        raise ReservationForbidden
    if reservation.status != ReservationStatus.ACTIVE:
        db.rollback()
        raise ReservationNotActive
    pallet = db.get(Pallet, reservation.pallet_id, with_for_update=True)
    reservation.status = ReservationStatus.CANCELLED.value
    if pallet is not None:
        pallet.status = PalletStatus.AVAILABLE.value
    db.commit()
    return reservation


def list_reservations(db: Session, user: User, limit: int, offset: int) -> list[Reservation]:
    query = select(Reservation).order_by(Reservation.id.desc()).limit(limit).offset(offset)
    if user.role != Role.ADMIN:
        query = query.where(Reservation.fund_id == user.fund_id)
    return list(db.scalars(query))
