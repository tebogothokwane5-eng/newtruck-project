import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# -----------------------------
# DATABASE CONFIG (SECURE)
# -----------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://myuser:98032854@localhost:5432/mydb"
)

# -----------------------------
# ENGINE (PRODUCTION SAFE)
# -----------------------------
engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # handles concurrent users
    max_overflow=20,
    pool_pre_ping=True,    # auto-reconnect broken connections
    pool_recycle=1800,     # avoids stale connections
    echo=False             # NEVER true in production
)

# -----------------------------
# SESSION
# -----------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# -----------------------------
# DEPENDENCY (FASTAPI)
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()   # IMPORTANT: prevents corrupted transactions
        raise e
    finally:
        db.close()