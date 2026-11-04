import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Na Vercel (środowisko serverless) katalog roboczy jest tylko do odczytu (/var/task),
# dlatego jako fallback SQLite używamy /tmp/timetracker.db. Docelowo używany jest DATABASE_URL (PostgreSQL).
default_sqlite = "sqlite:////tmp/timetracker.db" if os.environ.get("VERCEL") else "sqlite:///./timetracker.db"
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or default_sqlite
)

# Konwersja postgres:// -> postgresql:// wymagana przez SQLAlchemy 2.0 (dla Neon / Supabase / Render)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {"connect_args": connect_args}

if not is_sqlite:
    # W środowisku serverless (Vercel + Neon/Supabase) zapobiega zrywaniu nieaktywnych połączeń SSL
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
