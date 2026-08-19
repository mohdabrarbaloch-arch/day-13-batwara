"""Group endpoints: create, list, detail, add member, leave."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Group, User
from app.routers.auth import get_current_user
from app.schemas import GroupCreate, GroupDetail, GroupOut, UserOut

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


def _require_member(group: Group, user: User) -> None:
    if user not in group.members:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")


def _group_total_expenses(group: Group) -> float:
    return round(sum(float(e.amount) for e in group.expenses), 2)


def _to_group_out(group: Group) -> GroupOut:
    return GroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        currency=group.currency,
        created_at=group.created_at,
        members=[UserOut.model_validate(m) for m in group.members],
        total_expenses=_group_total_expenses(group),
    )


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    data: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = Group(
        name=data.name.strip(),
        description=data.description,
        currency=data.currency.upper(),
        created_by=current_user.id,
    )
    group.members.append(current_user)
    for email in data.member_emails:
        member = db.scalar(select(User).where(User.email == email.lower()))
        if member is not None and member not in group.members:
            group.members.append(member)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _to_group_out(group)


@router.get("", response_model=list[GroupOut])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    groups = db.scalars(
        select(Group).join(Group.members).where(User.id == current_user.id).order_by(Group.created_at.desc())
    ).all()
    return [_to_group_out(g) for g in groups]


@router.get("/{group_id}", response_model=GroupDetail)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    return GroupDetail(
        **_to_group_out(group).model_dump(),
        expenses=[],
    )


@router.post("/{group_id}/members", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def add_members(
    group_id: int,
    emails: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add members by email (only users already registered can be added)."""
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    added: list[User] = []
    for email in emails:
        member = db.scalar(select(User).where(User.email == email.strip().lower()))
        if member is not None and member not in group.members:
            group.members.append(member)
            added.append(member)
    db.commit()
    db.refresh(group)
    return _to_group_out(group)


@router.post("/{group_id}/leave", response_model=GroupOut)
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    if current_user not in group.members:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")
    group.members.remove(current_user)
    db.commit()
    db.refresh(group)
    return _to_group_out(group)
