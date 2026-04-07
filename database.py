from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# 🔥 Render ENV se URL lo
DATABASE_URL = os.getenv("DATABASE_URL")

# ❗ agar ENV missing ho to clear error
if not DATABASE_URL:
    raise Exception("DATABASE_URL not found. Set it in Render environment variables.")

# 🔥 engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# 🔥 session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 🔥 base
Base = declarative_base()

# 🔥 dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()