# Setup Guide

## Prerequisites

- Python 3.11+
- pip
- (optional) Docker + Docker Compose for the Postgres setup

## 1. Local development (SQLite)

```bash
# clone
git clone https://github.com/mohdabrarbaloch-arch/day-13-batwara.git
cd day-13-batwara

# virtualenv (recommended)
python -m venv .venv
source .venv/bin/activate

# install
pip install -r requirements.txt

# configure
cp .env.example .env
# edit .env → set a real SECRET_KEY

# run
uvicorn app.main:app --reload
```

Open http://localhost:8000 — the SPA is served from the same origin.
API docs: http://localhost:8000/docs

## 2. Docker + PostgreSQL

```bash
cp .env.example .env
docker compose up --build
```

`docker-compose.yml` starts Postgres 16 and the API, wired via
`DATABASE_URL=postgresql+psycopg2://batwara:batwara@db:5432/batwara`.

## 3. Run tests

```bash
pip install pytest httpx ruff
pytest -q          # 35 tests
ruff check .       # lint
```

## 4. Deploy to Vercel (serverless)

The repo is Vercel-ready: `vercel.json` routes `/api/*` to `api/index.py`
(which defaults to a `/tmp/batwara.db` SQLite for serverless) and serves the
SPA from `app/static/`.

```bash
npm i -g vercel
vercel --prod --yes
```

Set `SECRET_KEY` as an environment variable in the Vercel dashboard.

> Note: serverless SQLite resets on cold starts. For a persistent store on
> Vercel, point `DATABASE_URL` at a hosted Postgres (Neon, Supabase, Railway).
