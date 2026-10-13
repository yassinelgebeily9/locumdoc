"""Cookie consent and Firebase Analytics.

Analytics only ever runs for visitors who chose "Accept analytics" in the cookie banner, and
never in the admin area. The choice lives in the `ld_consent` cookie ("analytics" or
"essential"); it isn't HttpOnly so the banner can apply it without a page reload.

Firebase is configured with FIREBASE_WEB_CONFIG: the web-app config object from the Firebase
console (Project settings → Your apps), as JSON. Those values are public identifiers, not
secrets. Without it the banner still works and no analytics code is loaded.

Views report key moments with track("sign_up", method="doctor"); the event is held in the
session and sent from the next page the visitor sees, once analytics has loaded.
"""
import json

from flask import current_app, g, request, session

COOKIE = "ld_consent"
CHOICES = ("analytics", "essential")
MAX_AGE = 180 * 24 * 3600  # ask again after six months

# Hosts Firebase Analytics talks to (it loads Google's gtag.js and sends hits to Google Analytics).
CSP_SCRIPT = "https://www.googletagmanager.com"
CSP_CONNECT = ("https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com "
               "https://firebase.googleapis.com https://firebaseinstallations.googleapis.com")
CSP_IMG = "https://*.google-analytics.com https://www.googletagmanager.com"


def web_config():
    raw = current_app.config.get("FIREBASE_WEB_CONFIG") or ""
    if not raw:
        return None
    try:
        cfg = json.loads(raw)
    except ValueError:
        current_app.logger.warning("FIREBASE_WEB_CONFIG is not valid JSON; analytics is off.")
        return None
    keys = ("apiKey", "projectId", "appId", "measurementId")
    if not all(cfg.get(k) for k in keys):
        current_app.logger.warning("FIREBASE_WEB_CONFIG needs %s; analytics is off.", ", ".join(keys))
        return None
    return {k: cfg[k] for k in ("apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId",
                                "measurementId") if cfg.get(k)}


def consent():
    v = request.cookies.get(COOKIE)
    return v if v in CHOICES else None


def enabled_here():
    """Analytics may load on this page (if the visitor consents): configured, and not the admin area."""
    if request.path.startswith("/admin") or (g.get("user") and g.user["role"] == "admin"):
        return False
    return web_config() is not None


def track(name, **params):
    """Queue an analytics event for the next page view (sent only if the visitor allowed analytics)."""
    events = session.get("_events", [])[-9:]
    events.append({"name": name, "params": params})
    session["_events"] = events


def pending_events():
    return session.pop("_events", []) if "_events" in session else []
