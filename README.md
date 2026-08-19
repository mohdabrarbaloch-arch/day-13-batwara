# بٹوارہ Batwara — Split expenses. Settle smart.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-35%20passing-34d399)](tests/)
[![Lint](https://img.shields.io/badge/ruff-clean-34d399)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**Batwara** (Urdu: *division*) is a smart group expense splitter for friends,
flatmates, hostels and road trips. It tracks who paid what, computes exact
balances, and — the fun part — tells you the **minimum-transaction settlement
plan**: who should pay whom so the whole group settles up with the fewest
possible payments.

Built for Pakistan (PKR first), but the logic is currency-agnostic.

---

## ✨ Features

- 🧮 **Exact balance math** — no floating-point drift; shares are scaled precisely
- 🔁 **Debt simplification** — chains collapse (A owes B, B owes C → A pays C),
  zero-sum cycles detected (everyone nets zero → no payments at all)
- ⚡ **Two settlement strategies** — greedy (always valid) + optimal
  (zero-sum subset decomposition for fewer transactions)
- 💸 **Equal or exact splits** on every expense (e.g. someone didn't eat)
- 👥 **Groups & members** — create a group, add people by email
- 🔐 **Secure** — JWT auth, bcrypt password hashing, rate-limited endpoints
- 📱 **Mobile-first SPA** — no app store, works in any browser
- 🐳 **Docker-ready** — Postgres 16 via docker-compose, SQLite for local dev
- 🚀 **Vercel-ready** — serverless entrypoint included

## 🚀 Live Demo

*Deployment pending — see [Deployment](#deployment) below.*

## 🖼️ Screenshots

*Coming soon — the SPA is served at `/` when the API runs.*

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · SQLAlchemy 2.0 · Pydantic v2 |
| Auth | JWT (HS256) · bcrypt |
| Database | SQLite (dev) · PostgreSQL 16 (prod) |
| Frontend | Vanilla JS · mobile-first dark UI |
| Infra | Docker · Vercel |

## 📦 Installation

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-13-batwara.git
cd day-13-batwara

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env    # set a real SECRET_KEY
uvicorn app.main:app --reload
```

Open **http://localhost:8000** — the app is served from the same origin.
Interactive API docs at **http://localhost:8000/docs**.

### Docker

```bash
docker compose up --build
```

### Tests & lint

```bash
pytest -q        # 35 tests
ruff check .     # clean
```

Full instructions: [docs/setup.md](docs/setup.md) · [docs/usage.md](docs/usage.md) · [docs/api.md](docs/api.md) · [ARCHITECTURE.md](ARCHITECTURE.md)

## 🧠 How the settlement engine works

1. Every expense becomes per-member shares (equal or exact).
2. Balances: `net = paid − owes` for each member.
3. **Greedy**: settle the biggest creditor against the biggest debtor, repeat.
4. **Optimal**: look for zero-sum subsets of balances and settle them
   internally — this splits the problem and cuts the transaction count.

## 🔗 API Quick Reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT |
| POST | `/api/groups` | Create group |
| POST | `/api/groups/{id}/expenses` | Add expense |
| GET | `/api/groups/{id}/settle/plan` | Minimum-transaction plan |
| POST | `/api/groups/{id}/settle` | Record settlement |

Full reference: [docs/api.md](docs/api.md)

## 🚀 Deployment

**Vercel** — the repo is Vercel-ready:

```bash
npm i -g vercel
vercel --prod --yes
```

Set `SECRET_KEY` in the Vercel dashboard. Note: serverless SQLite resets on
cold starts — point `DATABASE_URL` at hosted Postgres (Neon/Supabase/Railway)
for persistence.

## 📄 License

MIT — see [LICENSE](LICENSE).

---

*Day 13 of the 30-day autonomous build challenge. Built by ABraz Baloch.*
