"""
Run this ONCE to create all tables and insert default admin user.
    python init_db.py
"""
from database import engine, SessionLocal
import models

# Create all tables
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check if admin already exists
existing = db.query(models.User).filter(models.User.email == "admin@edu.com").first()
if not existing:
    admin = models.User(name="Super Admin", email="admin@edu.com", password="admin123", role="admin")
    db.add(admin)
    db.commit()
    print("✅ Tables created!")
    print("✅ Default admin created → email: admin@edu.com | password: admin123")
else:
    print("⚠️  Admin already exists. Tables are ready.")

db.close()