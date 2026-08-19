"""Settlement endpoints: balances, settlement plan, record settlement."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Group, Settlement, User
from app.routers.auth import get_current_user
from app.routers.groups import _group_or_404, _require_member
from app.schemas import (
    BalanceOut,
    SettlementCreate,
    SettlementOut,
    SettlementPlanItem,
    SettlementPlanOut,
    UserOut,
)
from app.services.settlements import (
    compute_balances,
    greedy_settlement,
    optimal_settlement,
)

router = APIRouter(prefix="/api/groups/{group_id}/settle", tags=["settlements"])


def _expenses_to_balance_input(group: Group) -> list[tuple[int, float, dict[int, float]]]:
    """Convert group expenses into (payer_id, amount, shares) tuples."""
    result: list[tuple[int, float, dict[int, float]]] = []
    member_ids = [m.id for m in group.members]
    for expense in group.expenses:
        amount = float(expense.amount)
        if expense.split_type == "equal":
            shares = {mid: 1.0 for mid in member_ids}
        else:
            details = json.loads(expense.split_details or "{}")
            shares = {int(k): float(v) for k, v in details.items()}
        result.append((expense.paid_by_id, amount, shares))
    return result


@router.get("/balances", response_model=list[BalanceOut])
def get_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    balances = compute_balances(
        [m.id for m in group.members], _expenses_to_balance_input(group)
    )
    out: list[BalanceOut] = []
    for member in group.members:
        bal = balances.get(member.id)
        if bal is None:
            continue
        out.append(
            BalanceOut(
                user=UserOut.model_validate(member),
                paid=bal.paid,
                owes=bal.owes,
                net=bal.net,
            )
        )
    out.sort(key=lambda b: b.net, reverse=True)
    return out


@router.get("/plan", response_model=SettlementPlanOut)
def get_settlement_plan(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)

    member_ids = [m.id for m in group.members]
    balances = compute_balances(member_ids, _expenses_to_balance_input(group))

    plan, algorithm = optimal_settlement(balances)
    if algorithm != "optimal":
        plan = greedy_settlement(balances)

    user_map = {m.id: m for m in group.members}
    plan_items = [
        SettlementPlanItem(
            from_user=UserOut.model_validate(user_map[s.from_user]),
            to_user=UserOut.model_validate(user_map[s.to_user]),
            amount=s.amount,
        )
        for s in plan
        if s.from_user in user_map and s.to_user in user_map
    ]

    balance_items = []
    for member in group.members:
        bal = balances.get(member.id)
        if bal is not None:
            balance_items.append(
                BalanceOut(
                    user=UserOut.model_validate(member),
                    paid=bal.paid,
                    owes=bal.owes,
                    net=bal.net,
                )
            )

    total_expenses = round(sum(float(e.amount) for e in group.expenses), 2)
    return SettlementPlanOut(
        group_id=group_id,
        total_expenses=total_expenses,
        balances=balance_items,
        plan=plan_items,
        transactions=len(plan_items),
        algorithm=algorithm,
    )


@router.post("", response_model=SettlementOut, status_code=status.HTTP_201_CREATED)
def record_settlement(
    group_id: int,
    data: SettlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    recipient = db.get(User, data.to_user_id)
    if recipient is None or recipient not in group.members:
        raise HTTPException(status_code=400, detail="Recipient must be a group member")
    if recipient.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot settle with yourself")

    settlement = Settlement(
        group_id=group_id,
        from_user_id=current_user.id,
        to_user_id=data.to_user_id,
        amount=data.amount,
        note=data.note,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return SettlementOut.model_validate(settlement)


@router.get("/history", response_model=list[SettlementOut])
def settlement_history(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = _group_or_404(db, group_id)
    _require_member(group, current_user)
    settlements = (
        db.query(Settlement)
        .filter(Settlement.group_id == group_id)
        .order_by(Settlement.settled_at.desc())
        .all()
    )
    return [SettlementOut.model_validate(s) for s in settlements]
