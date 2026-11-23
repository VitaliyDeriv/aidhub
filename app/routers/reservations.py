from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.schemas import ReservationCreate, ReservationOut
from app.services import reservations as service

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=list[ReservationOut], status_code=status.HTTP_201_CREATED)
def create_reservation(payload: ReservationCreate, current: CurrentUser, db: DbSession):
    """Атомарно резервує набір палет для фонду поточного користувача."""
    try:
        return service.reserve_pallets(db, current, payload.pallet_ids)
    except service.NoFund:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only fund members can reserve pallets"
        ) from None
    except service.PalletsNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Pallets not found: {exc.ids}") from None
    except service.PalletsUnavailable as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Pallets already reserved: {exc.ids}"
        ) from None


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    current: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return service.list_reservations(db, current, limit, offset)


@router.get("/{reservation_id}", response_model=ReservationOut)
def read_reservation(reservation_id: int, current: CurrentUser, db: DbSession):
    try:
        return service.get_reservation(db, current, reservation_id)
    except service.ReservationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found") from None
    except service.ReservationForbidden:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Reservation belongs to another fund"
        ) from None


@router.delete("/{reservation_id}", response_model=ReservationOut)
def cancel_reservation(reservation_id: int, current: CurrentUser, db: DbSession):
    try:
        return service.cancel_reservation(db, current, reservation_id)
    except service.ReservationNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found") from None
    except service.ReservationForbidden:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Reservation belongs to another fund"
        ) from None
    except service.ReservationNotActive:
        raise HTTPException(status.HTTP_409_CONFLICT, "Reservation is not active") from None
