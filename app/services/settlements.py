"""Settlement algorithms: compute per-user balances and simplify debts.

Two strategies:
- greedy: the classic two-pointer approach that settles the largest creditor
  against the largest debtor, repeat. Always valid, at most n-1 transactions.
- optimal: tries to find a plan with fewer transactions by detecting zero-sum
  subsets of balances and settling them internally (dividing the problem into
  independent sub-problems). For small groups this often yields the true
  minimum number of transactions; when no useful subset is found it falls back
  to greedy. The exact minimum-transactions problem is NP-hard in general, so
  "optimal" is a well-performing heuristic, not a guarantee of global minimum.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

EPS = 1e-6


@dataclass
class Settlement:
    from_user: int
    to_user: int
    amount: float


@dataclass
class Balance:
    user_id: int
    paid: float = 0.0
    owes: float = 0.0

    @property
    def net(self) -> float:
        """Positive = receives money; negative = owes money."""
        return round(self.paid - self.owes, 2)


def compute_balances(
    members: list[int],
    expenses: list[tuple[int, float, dict[int, float]]],
) -> dict[int, Balance]:
    """Build net balances from expenses.

    Each expense is (payer_id, amount, {member_id: share}).
    """
    balances: dict[int, Balance] = {uid: Balance(uid) for uid in members}
    for payer_id, amount, shares in expenses:
        total_share = sum(shares.values())
        if total_share <= EPS:
            continue
        scale = amount / total_share
        for member_id, share in shares.items():
            if member_id not in balances:
                balances[member_id] = Balance(member_id)
            balances[member_id].owes += share * scale
        balances[payer_id].paid += amount
    for bal in balances.values():
        bal.paid = round(bal.paid, 2)
        bal.owes = round(bal.owes, 2)
    return balances


def _round_amount(x: float) -> float:
    return round(x + 1e-9, 2)


def greedy_settlement(balances: dict[int, Balance]) -> list[Settlement]:
    """Two-pointer greedy: largest creditor vs largest debtor, repeat."""
    creditors: list[tuple[float, int]] = []
    debtors: list[tuple[float, int]] = []
    for uid, bal in balances.items():
        if bal.net > EPS:
            creditors.append((bal.net, uid))
        elif bal.net < -EPS:
            debtors.append((-bal.net, uid))

    creditors.sort(reverse=True)
    debtors.sort(reverse=True)

    settlements: list[Settlement] = []
    i = j = 0
    while i < len(creditors) and j < len(debtors):
        credit, creditor_id = creditors[i]
        debt, debtor_id = debtors[j]
        amount = _round_amount(min(credit, debt))
        if amount > EPS:
            settlements.append(
                Settlement(from_user=debtor_id, to_user=creditor_id, amount=amount)
            )
        # Persist remaining balances back into the lists — otherwise the next
        # iteration re-reads the original amounts and over-settles.
        creditors[i] = (credit - amount, creditor_id)
        debtors[j] = (debt - amount, debtor_id)
        if creditors[i][0] <= EPS:
            i += 1
        if debtors[j][0] <= EPS:
            j += 1
    return settlements


def _find_zero_sum_subset(
    amounts: list[tuple[float, int]],
) -> list[tuple[float, int]] | None:
    """Find a non-trivial subset whose amounts sum (almost) to zero.

    Returns None if only the empty/full set qualifies. Uses meet-in-the-middle
    over pairs for subsets of size up to len(amounts)-1.
    """
    n = len(amounts)
    if n < 2:
        return None
    # Try all subset sizes from 1 to n-1 (avoid the full set which trivially
    # sums to zero when total is zero — we want strict subsets).
    for size in range(1, n):
        for combo in combinations(amounts, size):
            total = sum(a for a, _ in combo)
            if abs(total) <= EPS:
                return list(combo)
    return None


def optimal_settlement(balances: dict[int, Balance]) -> tuple[list[Settlement], str]:
    """Try to minimize transactions via zero-sum subset decomposition.

    Strategy: repeatedly find a subset of balances that nets to zero, settle
    those members internally with the greedy algorithm, then recurse on the
    remaining balances. Each internal settlement is independent of the rest.
    """
    items: list[tuple[float, int]] = []
    for uid, bal in balances.items():
        if abs(bal.net) > EPS:
            items.append((bal.net, uid))

    if not items:
        return [], "optimal"

    # Guard: this exact search is only practical for small groups.
    if len(items) > 12:
        return greedy_settlement(balances), "greedy"

    total_net = sum(a for a, _ in items)
    if abs(total_net) <= EPS:
        # Whole group nets to zero; still search subsets for fewer transactions.
        pass

    # Greedy over the full set gives an upper bound on the number of transactions.
    full_plan = greedy_settlement(balances)

    # Try to find a strict zero-sum subset to split off.
    subset = _find_zero_sum_subset(items)
    if subset is None or len(subset) in (0, len(items)):
        return full_plan, "greedy"

    subset_ids = {uid for _, uid in subset}
    sub_balances = {uid: bal for uid, bal in balances.items() if uid in subset_ids}
    rest_balances = {uid: bal for uid, bal in balances.items() if uid not in subset_ids}

    sub_plan = greedy_settlement(sub_balances)
    rest_plan, rest_algo = optimal_settlement(rest_balances)

    combined = sub_plan + rest_plan
    if len(combined) < len(full_plan):
        return combined, "optimal"
    return full_plan, "greedy"
