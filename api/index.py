"""Vercel serverless entrypoint."""
import os

# Vercel provides a read-write /tmp — use SQLite there for serverless.
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/batwara.db")

from app.main import app  # noqa: E402

handler = app
