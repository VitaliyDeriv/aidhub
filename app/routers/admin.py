from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.deps import DbSession, require_admin
from app.models import (
    Fund,
    Pallet,
    PalletStatus,
    Reservation,
    ReservationStatus,
    User,
    Warehouse,
)
from app.schemas import PalletBatchIn, PalletOut, StatsOut, UserOut, WarehouseIn, WarehouseOut

# Вертикальний контроль доступу: усі маршрути цього роутера лише для адміністратора.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession):
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
def create_warehouse(payload: WarehouseIn, db: DbSession):
    warehouse = Warehouse(name=payload.name, city=payload.city)
    db.add(warehouse)
    db.commit()
    return warehouse


@router.post("/pallets", response_model=list[PalletOut], status_code=status.HTTP_201_CREATED)
def create_pallets(payload: PalletBatchIn, db: DbSession):
    if db.get(Warehouse, payload.warehouse_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Warehouse not found")
    pallets = [
        Pallet(
            warehouse_id=payload.warehouse_id,
            description=payload.description,
            units=payload.units,
        )
        for _ in range(payload.count)
    ]
    db.add_all(pallets)
    db.commit()
    return pallets


@router.get("/stats", response_model=StatsOut)
def stats(db: DbSession):
    def count(query) -> int:
        return db.scalar(query) or 0

    return StatsOut(
        users=count(select(func.count(User.id))),
        funds=count(select(func.count(Fund.id))),
        pallets_total=count(select(func.count(Pallet.id))),
        pallets_available=count(
            select(func.count(Pallet.id)).where(Pallet.status == PalletStatus.AVAILABLE)
        ),
        pallets_reserved=count(
            select(func.count(Pallet.id)).where(Pallet.status == PalletStatus.RESERVED)
        ),
        active_reservations=count(
            select(func.count(Reservation.id)).where(Reservation.status == ReservationStatus.ACTIVE)
        ),
    )
