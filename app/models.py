"""SQLAlchemy models for Batwara."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Association: users <-> groups (membership)
group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    groups: Mapped[list[Group]] = relationship(
        secondary=group_members, back_populates="members", lazy="selectin"
    )
    expenses_paid: Mapped[list[Expense]] = relationship(
        back_populates="payer", foreign_keys="Expense.paid_by_id", lazy="selectin"
    )


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="PKR")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list[User]] = relationship(
        secondary=group_members, back_populates="groups", lazy="selectin"
    )
    expenses: Mapped[list[Expense]] = relationship(
        back_populates="group", cascade="all, delete-orphan", lazy="selectin"
    )


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="PKR")
    paid_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # How the expense is split: "equal" or "exact" (exact uses split_details)
    split_type: Mapped[str] = mapped_column(String(10), default="equal")
    split_details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON map user_id -> amount
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    group: Mapped[Group] = relationship(back_populates="expenses")
    payer: Mapped[User] = relationship(back_populates="expenses_paid", foreign_keys=[paid_by_id])


class Settlement(Base):
    """A completed settlement between two users in a group."""

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), index=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
