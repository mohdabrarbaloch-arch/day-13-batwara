"""Expense endpoints: create, list, delete."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expense, User
from app.routers.auth import get_current_user
from app.routers.groups import _group_or_404, _require_member
from app.schemas import ExpenseCreate, ExpenseOut, UserOut

router = APIRouter(prefix="/api/groups/{group_id}/expenses", tags=["expenses"])


def _expense_to_out(expense: Expense, viewer_id: int | None = None) -> ExpenseOut:
    split_details = None
    if expense.split_details:
        split_details = json.loads(expense.split_details)

    per_person_share = 0.0
    your_share = 0.0
    if expense.split_type == "equal" and expense.group.members:
        per_person_share = round(float(expense.amount) / len(expense.group.members), 2)
        if viewer_id is not None:
            your_share = per_person_share
    elif split_details:
        total_share = sum(float(v) for v in split_details.values())
        if total_share > 0 and viewer_id is not None and str(viewer_id) in split_details:
            your_share = round(
                float(expense.amount) * (float(split_details[str(viewer_id)]) / total_share), 2
            )

    return ExpenseOut(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        amount=float(expense.amount),
        currency=expense.currency,
        split_type=expense.split_type,
        split_details=split_details,
        created_at=expense.created_at,
        payer=UserOut.model_validate(expense.payer),
        per_person_share=per_person_share,
        your_share=your_share,
    )


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    group_id: int,
    data: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)

    if data.split_type == "exact":
        # Validate: every member in split_details must be a group member,
        # and shares must cover all members.
        member_ids = {m.id for m in group.members}
        detail_ids = {int(k) for k in data.split_details or {}}
        if not detail_ids:
            raise HTTPException(status_code=400, detail="split_details required for exact split")
        if not detail_ids.issubset(member_ids):
            raise HTTPException(status_code=400, detail="split_details contains non-members")
        # Amount check: sum of shares (scaled) must equal amount
        total_share = sum(float(v) for v in data.split_details.values())
        if abs(total_share - data.amount) > 0.02:
            raise HTTPException(
                status_code=400,
                detail=f"Exact shares sum to {total_share:.2f} but amount is {data.amount:.2f}",
            )
        split_details = json.dumps({str(k): float(v) for k, v in data.split_details.items()})
    else:
        split_details = None

    expense = Expense(
        group_id=group_id,
        description=data.description.strip(),
        amount=data.amount,
        currency=data.currency.upper(),
        paid_by_id=current_user.id,
        split_type=data.split_type,
        split_details=split_details,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return _expense_to_out(expense, viewer_id=current_user.id)


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    expenses = sorted(group.expenses, key=lambda e: e.created_at, reverse=True)
    return [_expense_to_out(e, viewer_id=current_user.id) for e in expenses]


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    group_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    expense = db.get(Expense, expense_id)
    if expense is None or expense.group_id != group_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    if expense.paid_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the payer can delete")
    db.delete(expense)
    db.commit()
