"""Sign-in helpers (Supabase Auth, called from the backend).

The browser never talks to Supabase directly. It sends email + password to
POST /api/auth/login, and gets back a short-lived access token that it sends
as `Authorization: Bearer <token>` on every request.

Demo accounts are REAL Supabase users with real roles (created once with
scripts/create_demo_users.py). The "Sign in as ..." buttons just sign in to
those accounts. Turn them off with ALLOW_DEMO_LOGIN=false.
"""
import logging
import os

from supabase import create_client

from app.db import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("mohar.auth")

DEMO_EMAILS = {
    "Creator": "creator@mohar-demo.app",
    "Manager": "manager@mohar-demo.app",
    "Reviewer": "reviewer@mohar-demo.app",
}


class AuthError(Exception):
    pass


def demo_enabled() -> bool:
    return os.getenv("ALLOW_DEMO_LOGIN", "true").strip().lower() != "false" and bool(os.getenv("DEMO_PASSWORD"))


def sign_in_password(email: str, password: str) -> dict:
    """Returns {'access_token', 'expires_in', 'user_id', 'email'}. Raises AuthError on bad credentials."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise AuthError("Server is not configured for sign-in.")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)  # separate client: never reused for table queries
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        # The real reason goes to the server log only (never to the browser, never the password).
        logger.warning("sign-in failed for %s: %s: %s", email, type(exc).__name__, str(exc)[:200])
        raise AuthError("Wrong email or password.")
    if res is None or res.session is None or res.user is None:
        raise AuthError("Wrong email or password.")
    return {
        "access_token": res.session.access_token,
        "expires_in": res.session.expires_in,
        "user_id": res.user.id,
        "email": res.user.email,
    }


def demo_sign_in(role: str) -> dict:
    if not demo_enabled():
        raise AuthError("Demo sign-in is turned off.")
    email = DEMO_EMAILS.get(role)
    if not email:
        raise AuthError("Unknown demo role.")
    return sign_in_password(email, os.environ["DEMO_PASSWORD"])
