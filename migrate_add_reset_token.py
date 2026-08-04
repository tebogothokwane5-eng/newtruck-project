"""
One-time migration: adds reset_token and reset_token_expiry columns to the
live `users` table.

Run this from an environment with access to the real production DATABASE_URL
- i.e. Render's Shell tab (Dashboard -> your service -> Shell), NOT your
local machine (unless your local DATABASE_URL is also pointed at production).

    python migrate_add_reset_token.py

Safe to run multiple times - it checks for the columns first and skips if
they already exist.
"""

from sqlalchemy import inspect, text
from backend.database import engine


def main():
    inspector = inspect(engine)
    existing_columns = {c["name"] for c in inspector.get_columns("users")}

    with engine.begin() as conn:
        if "reset_token" not in existing_columns:
            print("Adding reset_token column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(255)"))
            print("reset_token added")
        else:
            print("reset_token already exists, skipping")

        if "reset_token_expiry" not in existing_columns:
            print("Adding reset_token_expiry column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expiry TIMESTAMPTZ"))
            print("reset_token_expiry added")
        else:
            print("reset_token_expiry already exists, skipping")

    print("")
    print("Done. Verifying final schema:")
    inspector = inspect(engine)
    for col in inspector.get_columns("users"):
        if col["name"] in ("reset_token", "reset_token_expiry"):
            print(f"  - {col['name']}: {col['type']}")


if __name__ == "__main__":
    main()
