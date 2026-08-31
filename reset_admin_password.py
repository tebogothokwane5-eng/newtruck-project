import os
"""
Directly sets a known password for the admin user (id=4), bypassing email.

Run with production DATABASE_URL:
    DATABASE_URL="your_external_db_url" python reset_admin_password.py
"""
from backend.database import SessionLocal
from backend.models.user import User
from backend.models.payment import Payment
from backend.utils.security import hash_password

NEW_PASSWORD = os.getenv("NEW_ADMIN_PASSWORD", "AdminTest456!")

db = SessionLocal()
try:
    user = db.query(User).filter(User.id == 4).first()
    if not user:
        print("User id=4 not found")
    else:
        user.password = hash_password(NEW_PASSWORD)
        db.commit()
        print(f"Password updated for username={user.username}")
finally:
    db.close()
