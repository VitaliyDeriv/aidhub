from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Pallet, PalletStatus, Warehouse
from app.schemas import PalletOut, WarehouseOut

router = APIRouter(tags=["catalog"])


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(_: CurrentUser, db: DbSession):
    return list(db.scalars(select(Warehouse).order_by(Warehouse.id)))


@router.get("/pallets", response_model=list[PalletOut])
def list_pallets(
    _: CurrentUser,
    db: DbSession,
    status: PalletStatus | None = None,
    warehouse_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    query = select(Pallet).order_by(Pallet.id).limit(limit).offset(offset)
    if status is not None:
        query = query.where(Pallet.status == status.value)
    if warehouse_id is not None:
        query = query.where(Pallet.warehouse_id == warehouse_id)
    return list(db.scalars(query))
