"""
One-time migration: adds fcm_token column to the live `users` table.

Run this locally with your production DATABASE_URL set (same approach used
for the reset_token migration):

    DATABASE_URL="your_external_db_url" python migrate_add_fcm_token.py

Safe to run multiple times.
"""

from sqlalchemy import inspect, text
from backend.database import engine


def main():
    inspector = inspect(engine)
    existing_columns = {c["name"] for c in inspector.get_columns("users")}

    with engine.begin() as conn:
        if "fcm_token" not in existing_columns:
            print("Adding fcm_token column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN fcm_token VARCHAR(255)"))
            print("fcm_token added")
        else:
            print("fcm_token already exists, skipping")

    print("")
    print("Done. Verifying final schema:")
    inspector = inspect(engine)
    for col in inspector.get_columns("users"):
        if col["name"] == "fcm_token":
            print(f"  - {col['name']}: {col['type']}")


if __name__ == "__main__":
    main()
