import os
import ssl
import traceback
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

default_sqlite = "sqlite:////tmp/timetracker.db" if os.environ.get("VERCEL") else "sqlite:///./timetracker.db"

# Szukamy URL bazy Postgres ze wszystkich standardowych zmiennych Vercel / Neon / Supabase
CANDIDATE_ENV_KEYS = [
    "DATABASE_URL",
    "POSTGRES_URL",
    "STORAGE_DATABASE_URL",
    "STORAGE_POSTGRES_URL",
    "STORAGE_URL",
    "NEON_DATABASE_URL",
    "POSTGRES_PRISMA_URL",
]

raw_url = None
matched_env_key = None
for key in CANDIDATE_ENV_KEYS:
    val = os.environ.get(key)
    if val and val.strip():
        raw_url = val.strip()
        matched_env_key = key
        break

if not raw_url:
    raw_url = default_sqlite
    matched_env_key = "default_sqlite"

ENGINE_ERROR = None
ACTIVE_DRIVER = None


def _build_engine(url: str):
    global ACTIVE_DRIVER
    if url.startswith("sqlite"):
        ACTIVE_DRIVER = "sqlite"
        return create_engine(url, connect_args={"check_same_thread": False})

    # Normalizacja schematu dla Postgresa
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    parsed = urlparse(url)

    # 1. Próba przez psycopg2 z oczyszczonymi parametrami query
    try:
        allowed_params = {"sslmode", "connect_timeout", "application_name"}
        clean_query = [(k, v) for k, v in parse_qsl(parsed.query) if k in allowed_params]
        if not any(k == "sslmode" for k, _ in clean_query):
            clean_query.append(("sslmode", "require"))
        psycopg2_url = urlunparse(parsed._replace(scheme="postgresql+psycopg2", query=urlencode(clean_query)))
        eng = create_engine(psycopg2_url, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        ACTIVE_DRIVER = "postgresql+psycopg2"
        return eng
    except Exception as e1:
        # 2. Fallback na czysty sterownik Python pg8000 (niezależny od bibliotek C libpq na Serverless)
        try:
            pg8000_url = urlunparse(parsed._replace(scheme="postgresql+pg8000", query=""))
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            eng = create_engine(
                pg8000_url,
                connect_args={"ssl_context": ssl_ctx},
                pool_pre_ping=True,
            )
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            ACTIVE_DRIVER = "postgresql+pg8000"
            return eng
        except Exception as e2:
            raise RuntimeError(f"psycopg2 error: {e1} | pg8000 error: {e2}")


try:
    engine = _build_engine(raw_url)
    DATABASE_URL = raw_url
    is_sqlite = DATABASE_URL.startswith("sqlite")
except Exception:
    ENGINE_ERROR = traceback.format_exc()
    DATABASE_URL = default_sqlite
    is_sqlite = True
    ACTIVE_DRIVER = "sqlite_fallback"
    engine = create_engine(default_sqlite, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
