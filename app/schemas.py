from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, pattern=EMAIL_PATTERN, max_length=254),
]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: Email
    password: Password
    full_name: ShortText
    fund_name: ShortText


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    fund_id: int | None


class UserUpdate(BaseModel):
    full_name: ShortText | None = None
    password: Password | None = None


class WarehouseIn(BaseModel):
    name: ShortText
    city: ShortText


class WarehouseOut(ORMModel):
    id: int
    name: str
    city: str


class PalletBatchIn(BaseModel):
    warehouse_id: int
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    units: Annotated[int, Field(gt=0, le=100_000)]
    count: Annotated[int, Field(ge=1, le=500)] = 1


class PalletOut(ORMModel):
    id: int
    warehouse_id: int
    description: str
    units: int
    status: str


class ReservationCreate(BaseModel):
    pallet_ids: Annotated[list[int], Field(min_length=1, max_length=50)]


class ReservationOut(ORMModel):
    id: int
    pallet_id: int
    fund_id: int
    status: str
    created_at: datetime


class StatsOut(BaseModel):
    users: int
    funds: int
    pallets_total: int
    pallets_available: int
    pallets_reserved: int
    active_reservations: int
