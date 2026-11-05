import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

default_sqlite = "sqlite:////tmp/timetracker.db" if os.environ.get("VERCEL") else "sqlite:///./timetracker.db"
raw_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("STORAGE_URL")
    or default_sqlite
).strip()

if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

# Oczyszczenie niestandardowych parametrów query (np. pgbouncer, supa, channel_binding),
# które potrafią powodować błąd połączenia w sterowniku psycopg2
if raw_url.startswith("postgresql://"):
    parsed = urlparse(raw_url)
    allowed_params = {"sslmode", "connect_timeout", "application_name"}
    clean_query = [(k, v) for k, v in parse_qsl(parsed.query) if k in allowed_params]
    raw_url = urlunparse(parsed._replace(query=urlencode(clean_query)))

DATABASE_URL = raw_url
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {"connect_args": connect_args}

if not is_sqlite:
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
