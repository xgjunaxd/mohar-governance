"""One-time setup: creates the 3 demo accounts (Creator, Manager, Reviewer) in Supabase Auth
and assigns their roles in the user_roles table.

Run on your own computer from the repo root:
    pip install supabase python-dotenv
    # .env must contain SUPABASE_URL and SUPABASE_KEY (the SERVICE ROLE key) and DEMO_PASSWORD
    python scripts/create_demo_users.py

Safe to run again: existing users are left alone and their roles are re-applied.
"""
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
URL, KEY, PASSWORD = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"), os.getenv("DEMO_PASSWORD")
if not (URL and KEY and PASSWORD):
    sys.exit("Set SUPABASE_URL, SUPABASE_KEY (service role key) and DEMO_PASSWORD in .env first.")
if len(PASSWORD) < 10:
    sys.exit("DEMO_PASSWORD must be at least 10 characters.")

ACCOUNTS = {
    "creator@mohar-demo.app": "creator",
    "manager@mohar-demo.app": "manager",
    "reviewer@mohar-demo.app": "reviewer",
}
db = create_client(URL, KEY)

existing = {u.email: u for u in db.auth.admin.list_users()}
for email, role in ACCOUNTS.items():
    user = existing.get(email)
    if user is None:
        user = db.auth.admin.create_user({"email": email, "password": PASSWORD, "email_confirm": True}).user
        print(f"created {email}")
    else:
        print(f"exists  {email}")
    db.table("user_roles").upsert({"user_id": user.id, "email": email, "role": role}).execute()
    print(f"  role -> {role}")
print("Done. Never commit your .env file.")
