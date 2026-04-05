import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Odczytujemy DATABASE_URL z chmury Render (lub używamy lokalnego SQLite jako fallback)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./timetracker.db")

# Zabezpieczenie na przypadek baz Postgres (Postgres z chmury zaczyna URL od postgres://, a SQLAlchemy wymaga postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Dla SQLite wymagamy opcji check_same_thread, dla Postgres tej opcji nie ma
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
