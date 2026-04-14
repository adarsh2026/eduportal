from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ✅ Render / Production ke liye DATABASE_URL (env se)
DATABASE_URL = os.getenv("DATABASE_URL")

# 🔁 Fix for Render (postgres:// → postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://")

# ❌ Agar DATABASE_URL missing hai to clear error do
if not DATABASE_URL:
    raise Exception("DATABASE_URL is not set")

# ✅ Engine create (safe for production)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True  # connection drop issue avoid karega
)

# ✅ Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ✅ Base
Base = declarative_base()

# ✅ Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
