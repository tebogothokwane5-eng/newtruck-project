"""
Lists all users with role='admin'.

Run with production DATABASE_URL:
    DATABASE_URL="your_external_db_url" python check_admin_user.py
"""
from backend.database import SessionLocal
from backend.models.user import User
from backend.models.payment import Payment  # needed so SQLAlchemy can resolve WorkOrder's relationship

db = SessionLocal()
try:
    admins = db.query(User).filter(User.role == "admin").all()
    if not admins:
        print("No admin users found in the database.")
    else:
        for u in admins:
            print(f"id={u.id}, username={u.username}, email={u.email}, is_active={u.is_active}")
finally:
    db.close()
