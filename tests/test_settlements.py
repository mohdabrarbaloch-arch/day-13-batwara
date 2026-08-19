"""Tests for the settlement engine — the heart of Batwara."""
import pytest

from app.services.settlements import (
    Balance,
    compute_balances,
    greedy_settlement,
    optimal_settlement,
)

EPS = 1e-6


def settle_map(plan):
    return {(s.from_user, s.to_user): s.amount for s in plan}


def assert_plan_valid(plan, balances):
    """A valid plan must clear every balance exactly.

    net positive = owed money (creditor); a debtor paying increases their net.
    """
    net = {uid: bal.net for uid, bal in balances.items()}
    for s in plan:
        net[s.from_user] += s.amount
        net[s.to_user] -= s.amount
    for uid, value in net.items():
        assert abs(value) <= 0.02, f"balance {uid} not cleared: {value}"


class TestComputeBalances:
    def test_single_payer_equal_split(self):
        # Ali pays 3000 for all three, equal split
        b = compute_balances([1, 2, 3], [(1, 3000.0, {1: 1, 2: 1, 3: 1})])
        assert b[1].net == pytest.approx(2000.0)
        assert b[2].net == pytest.approx(-1000.0)
        assert b[3].net == pytest.approx(-1000.0)

    def test_two_payers(self):
        b = compute_balances(
            [1, 2, 3],
            [(1, 3000.0, {1: 1, 2: 1, 3: 1}), (2, 1500.0, {1: 1, 2: 1, 3: 1})],
        )
        assert b[1].net == pytest.approx(1500.0)
        assert b[2].net == pytest.approx(0.0)
        assert b[3].net == pytest.approx(-1500.0)

    def test_exact_split_shares(self):
        # Dinner 1000: Ali 500, Bilal 300, Sara 200 (paid by Ali)
        b = compute_balances([1, 2, 3], [(1, 1000.0, {1: 500.0, 2: 300.0, 3: 200.0})])
        assert b[1].net == pytest.approx(500.0)
        assert b[2].net == pytest.approx(-300.0)
        assert b[3].net == pytest.approx(-200.0)

    def test_zero_sum_when_everyone_pays_equally(self):
        b = compute_balances(
            [1, 2, 3],
            [(1, 500.0, {1: 1, 2: 1, 3: 1}), (2, 500.0, {1: 1, 2: 1, 3: 1}), (3, 500.0, {1: 1, 2: 1, 3: 1})],
        )
        for bal in b.values():
            assert abs(bal.net) <= EPS


class TestGreedySettlement:
    def test_simple_three_way(self):
        b = compute_balances([1, 2, 3], [(1, 3000.0, {1: 1, 2: 1, 3: 1})])
        plan = greedy_settlement(b)
        assert_plan_valid(plan, b)
        assert len(plan) == 2

    def test_chain_collapses(self):
        # A owes B 100, B owes C 100 → A pays C 100 directly
        b = compute_balances([1, 2, 3], [(2, 100.0, {1: 1}), (3, 100.0, {2: 1})])
        plan = greedy_settlement(b)
        assert_plan_valid(plan, b)
        assert len(plan) == 1
        assert (1, 3) in settle_map(plan)
        assert settle_map(plan)[(1, 3)] == pytest.approx(100.0)

    def test_cycle_cancels_to_zero(self):
        b = compute_balances(
            [1, 2, 3],
            [(1, 500.0, {2: 1}), (2, 500.0, {3: 1}), (3, 500.0, {1: 1})],
        )
        plan = greedy_settlement(b)
        assert plan == []

    def test_four_way_mixed(self):
        b = compute_balances(
            [1, 2, 3, 4],
            [(1, 2000.0, {1: 1, 2: 1, 3: 1, 4: 1}), (2, 1000.0, {1: 1, 2: 1, 3: 1, 4: 1})],
        )
        plan = greedy_settlement(b)
        assert_plan_valid(plan, b)
        # Net: u1 +1250, u2 +250, u3 -750, u4 -750 → exactly 3 payments minimum
        assert len(plan) == 3


class TestOptimalSettlement:
    def test_returns_valid_plan(self):
        b = compute_balances([1, 2, 3], [(1, 3000.0, {1: 1, 2: 1, 3: 1})])
        plan, algo = optimal_settlement(b)
        assert_plan_valid(plan, b)

    def test_optimal_no_worse_than_greedy(self):
        # Case where subset decomposition helps:
        # A paid 100 (A,B), B paid 100 (B,C), C paid 100 (C,A) — everyone nets 0
        # plus a separate A owes D 50.
        b = compute_balances(
            [1, 2, 3, 4],
            [(1, 100.0, {1: 1, 2: 1}), (2, 100.0, {2: 1, 3: 1}), (3, 100.0, {3: 1, 1: 1}), (4, 50.0, {1: 1})],
        )
        greedy = greedy_settlement(b)
        optimal, algo = optimal_settlement(b)
        assert_plan_valid(optimal, b)
        assert len(optimal) <= len(greedy)

    def test_empty_balances(self):
        plan, algo = optimal_settlement({})
        assert plan == []

    def test_single_balance_returns_empty(self):
        b = {1: Balance(1, paid=100.0, owes=0.0)}
        plan, algo = optimal_settlement(b)
        assert plan == []

    def test_large_group_falls_back_to_greedy(self):
        # 13 members — exceeds the exact-search threshold
        members = list(range(1, 14))
        expenses = [(1, 5000.0, {m: 1 for m in members})]
        b = compute_balances(members, expenses)
        plan, algo = optimal_settlement(b)
        assert algo == "greedy"
        # 12 debtors all pay the payer (rounding accumulates, so check loosely)
        assert len(plan) == 12
        for s in plan:
            assert s.to_user == 1
            assert abs(s.amount - 5000 / 13) < 0.1
