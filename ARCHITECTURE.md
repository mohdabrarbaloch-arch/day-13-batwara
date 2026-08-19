# Batwara (بٹوارہ) — Architecture

> **Batwara** = Urdu for *division / distribution*. A smart group expense splitter
> that tells you exactly who owes whom — and settles it in the fewest payments.

## System Overview

```
┌────────────────────┐        ┌─────────────────────────────┐        ┌──────────────┐
│   Mobile-first     │  REST  │         FastAPI API         │  ORM   │    Database  │
│   SPA (vanilla JS) │ ─────► │  auth · groups · expenses   │ ─────► │   SQLite     │
│   /static/         │  ◄───── │  settle · balances · plan   │ ◄───── │  / Postgres  │
└────────────────────┘   JSON │  (JWT-secured, rate-limited)│        └──────────────┘
                              └─────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115 (Python 3.11), Pydantic v2 |
| Auth | JWT (HS256, 24h expiry) + bcrypt (12 rounds) |
| Database | SQLAlchemy 2.0 ORM — SQLite (dev) / PostgreSQL 16 (docker-compose) |
| Real-time | N/A — settled state is computed on request |
| Frontend | Vanilla JS SPA, mobile-first, dark UI (no build step) |
| Security | CORS allow-list, slowapi rate limits, input validation, secrets via env |
| Infra | Docker, docker-compose, Vercel-ready (serverless entrypoint) |

## Data Model

- **users** — id, name, email (unique), password_hash, created_at
- **groups** — id, name, description, currency, created_by, created_at
  - `group_members` (M2M: users ↔ groups)
- **expenses** — id, group_id, description, amount, currency, paid_by_id,
  split_type (`equal` | `exact`), split_details (JSON map user_id → share),
  created_at
- **settlements** — id, group_id, from_user_id, to_user_id, amount, note, settled_at

## Settlement Engine (`app/services/settlements.py`)

1. **Balance computation** — for every member, `net = paid − owes`.
   - Equal split: shares are 1 per member, scaled by `amount / Σ shares`.
   - Exact split: shares from `split_details`, scaled the same way.
2. **Debt simplification** — two strategies:
   - **greedy**: largest creditor ↔ largest debtor, settle the min, repeat.
     Always valid, ≤ n−1 transactions.
   - **optimal**: finds zero-sum subsets of balances and settles them
     internally, splitting the problem into independent sub-problems. For
     small groups this reduces the transaction count; falls back to greedy
     for groups > 12 non-zero balances (the exact minimum-transactions
     problem is NP-hard).

The plan endpoint returns the algorithm used, so the UI can label it.

## API Surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | — | Create account |
| POST | `/api/auth/login` | — | Get JWT |
| GET | `/api/auth/me` | JWT | Current user |
| POST | `/api/groups` | JWT | Create group |
| GET | `/api/groups` | JWT | List my groups |
| GET | `/api/groups/{id}` | JWT | Group detail |
| POST | `/api/groups/{id}/members` | JWT | Add members by email |
| POST | `/api/groups/{id}/leave` | JWT | Leave group |
| POST | `/api/groups/{id}/expenses` | JWT | Add expense |
| GET | `/api/groups/{id}/expenses` | JWT | List expenses |
| DELETE | `/api/groups/{id}/expenses/{eid}` | JWT | Delete expense (payer only) |
| GET | `/api/groups/{id}/settle/balances` | JWT | Per-user balances |
| GET | `/api/groups/{id}/settle/plan` | JWT | Minimum-transaction plan |
| POST | `/api/groups/{id}/settle` | JWT | Record a settlement |
| GET | `/api/groups/{id}/settle/history` | JWT | Settlement history |
| GET | `/api/health` | — | Health check |

## Security

- Passwords hashed with bcrypt (cost 12) — never stored in plaintext.
- JWT bearer tokens, 24h expiry, `sub` = user id.
- Slowapi rate limiting: 10/min on auth endpoints, 60/min default.
- CORS restricted via `CORS_ORIGINS` env (default `*` for dev).
- `SECRET_KEY` must be set in production (`openssl rand -hex 32`).
- Pydantic validation on every request body.

## Scaling Notes

- **SQLite → Postgres**: swap `DATABASE_URL`; SQLAlchemy models are portable.
- Read-heavy groups can add a Redis cache on balances (they're computed per
  request today — fine for groups of < 100 members).
- The settlement engine is O(n²) worst case on zero-sum subset search; the
  >12-members guard keeps worst-case bounded.
- Stateless API + JWT → horizontal scaling is trivial; Postgres is the only
  shared state.

## Run Locally

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
# → http://localhost:8000
```

Or with Docker:

```bash
docker compose up --build
# → http://localhost:8000
```
