import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _database_url() -> str:
    """Postgres in production (Vercel), SQLite locally.

    Vercel's filesystem is ephemeral and read-only outside /tmp, so a hosted
    Postgres (Neon / Supabase / Vercel Postgres) is what keeps data alive there.
    Set DATABASE_URL in Project → Settings → Environment Variables.
    """
    url = os.environ.get("DATABASE_URL", "").strip()

    if url:
        # Neon/Supabase/Heroku hand out postgres://, SQLAlchemy wants postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    if os.environ.get("VERCEL"):
        # No DB configured on Vercel — boot on a throwaway file so the site
        # still renders instead of 500-ing. Data resets on every cold start.
        return "sqlite:////tmp/we.db"

    return "sqlite:///" + os.path.join(BASE_DIR, "we.db")


SQLALCHEMY_DATABASE_URL = _database_url()

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # serverless: connections die between invocations, so check before reusing
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency — hands out a session and always closes it.

    Matters more than it looks on serverless: an unclosed session holds a
    Postgres connection open until the lambda dies.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
