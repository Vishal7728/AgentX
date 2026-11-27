from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def init_db():
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # Lightweight additive migration for existing v1 databases.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS folder_mode VARCHAR(20) NOT NULL DEFAULT 'post'"))
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS archive_name VARCHAR(80) NOT NULL DEFAULT 'X Archive'"))
