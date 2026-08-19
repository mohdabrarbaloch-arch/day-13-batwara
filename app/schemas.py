"""Pydantic schemas (request/response models)."""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# ── Auth ────────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("password must contain letters and digits")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Groups ──────────────────────────────────────────────────────────────


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    currency: str = Field(default="PKR", max_length=8)
    member_emails: list[EmailStr] = Field(default_factory=list, max_length=50)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    currency: str
    created_at: datetime
    members: list[UserOut]
    total_expenses: float = 0.0


class GroupDetail(GroupOut):
    expenses: list[ExpenseOut] = []


# ── Expenses ────────────────────────────────────────────────────────────


class ExpenseCreate(BaseModel):
    description: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(default="PKR", max_length=8)
    split_type: str = Field(default="equal", pattern="^(equal|exact)$")
    # For exact split: map of member user_id -> share amount
    split_details: dict[int, float] | None = None

    @field_validator("split_details")
    @classmethod
    def validate_split_details(cls, v: dict[int, float] | None) -> dict[int, float] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("split_details must not be empty")
        if any(x <= 0 for x in v.values()):
            raise ValueError("shares must be positive")
        return v


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    description: str
    amount: float
    currency: str
    split_type: str
    split_details: dict[str, float] | None
    created_at: datetime
    payer: UserOut
    per_person_share: float = 0.0
    your_share: float = 0.0


# ── Balances & settlements ──────────────────────────────────────────────


class BalanceOut(BaseModel):
    user: UserOut
    paid: float = 0.0
    owes: float = 0.0
    net: float = 0.0  # positive = gets money back, negative = owes money


class SettlementPlanItem(BaseModel):
    from_user: UserOut
    to_user: UserOut
    amount: float


class SettlementPlanOut(BaseModel):
    group_id: int
    total_expenses: float
    balances: list[BalanceOut]
    plan: list[SettlementPlanItem]
    transactions: int
    algorithm: str


class SettlementCreate(BaseModel):
    to_user_id: int
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=200)


class SettlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    from_user_id: int
    to_user_id: int
    amount: float
    note: str | None
    settled_at: datetime


GroupDetail.model_rebuild()
