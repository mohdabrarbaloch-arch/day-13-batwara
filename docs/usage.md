# Usage Guide

Batwara is a group expense splitter. Here's how to use it.

## Quick start

1. **Register** — create an account (name, email, password ≥ 8 chars with letters + digits).
2. **Create a group** — give it a name; optionally add members by email
   (they must already have Batwara accounts).
3. **Add expenses** — tap **+**, describe the expense, enter the amount in PKR,
   and choose how to split:
   - **Equally** among all members (default), or
   - **Exact** amounts per person (e.g. dinner where someone didn't eat).
4. **Check balances** — the Balances tab shows each member's `paid`, `owes`,
   and net position (gets back / owes).
5. **Settle up** — the *Settle plan* tab shows the minimum-transaction plan:
   who should pay whom, and how much. Pay however you like (JazzCash,
   Easypaisa, cash) — Batwara just keeps the ledger straight.

## Features

- **Exact math** — balances are computed with scaling, not naive division, so
  rounding errors don't accumulate.
- **Minimum-transaction plans** — the engine collapses chains (A owes B, B
  owes C → A pays C) and detects zero-sum cycles (everyone nets zero → no
  payment needed).
- **Equal or exact splits** on every expense.
- **Settlement history** — record payments so the group ledger stays current.
- **Secure** — JWT auth, bcrypt hashing, rate-limited endpoints.
- **Mobile-first** — works great on a phone; no app store needed.

## Example

Three friends — Ali, Bilal, Sara — go on a road trip:

- Ali pays Rs 3,000 for fuel.
- Bilal pays Rs 1,500 for food.
- Equal split, 3 ways.

Balances: Ali nets **+1500** (gets back), Bilal nets **0**, Sara nets **−1500** (owes).

Plan: **Sara pays Ali Rs 1,500.** One transaction. Done.

## Deleting expenses

Only the person who paid can delete an expense. Tap 🗑 next to it — it's
removed and balances recalculate.
