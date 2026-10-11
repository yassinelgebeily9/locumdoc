import hmac
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

from .db import query


# ------------------------------------------------------------------ sessions

def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        user = query("SELECT * FROM users WHERE id = ? AND is_active = 1", (uid,), one=True)
        # Invalidate the session if the password changed since login.
        if user and session.get("pwv") == user["password_hash"][-12:]:
            g.user = user
        else:
            session.clear()


def login_user(user):
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    session["pwv"] = user["password_hash"][-12:]
    session["csrf"] = secrets.token_urlsafe(32)


def login_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Log in to continue.", "info")
                return redirect(url_for("auth.login", next=request.full_path))
            if roles and g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


# ---------------------------------------------------------------------- CSRF

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def check_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not sent or not hmac.compare_digest(sent, session.get("csrf", "")):
            abort(400, description="Your session expired. Reload the page and try again.")


# ---------------------------------------------------------------- rate limit

_attempts = defaultdict(deque)


def rate_limited(key, limit=8, window=600):
    """Simple in-process limiter: True when `key` exceeded `limit` hits in `window` seconds."""
    now = time.time()
    q = _attempts[key]
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def client_ip():
    return (request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0]).strip()
