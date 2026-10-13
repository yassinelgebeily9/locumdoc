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
import re

from flask import current_app, g, request, session

COOKIE = "ld_consent"
CHOICES = ("analytics", "essential")
MAX_AGE = 180 * 24 * 3600  # ask again after six months

# Hosts Firebase Analytics talks to (it loads Google's gtag.js and sends hits to Google Analytics).
CSP_SCRIPT = "https://www.googletagmanager.com"
CSP_CONNECT = ("https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com "
               "https://firebase.googleapis.com https://firebaseinstallations.googleapis.com")
CSP_IMG = "https://*.google-analytics.com https://www.googletagmanager.com"
# Hosts Google sign-in (Firebase Authentication) uses: its helper script, and the token endpoints.
CSP_AUTH_SCRIPT = "https://apis.google.com"
CSP_AUTH_CONNECT = "https://identitytoolkit.googleapis.com https://securetoken.googleapis.com"


FIELDS = ("apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId", "measurementId")


def parse_web_config(raw):
    """Read the web-app config as JSON, or exactly as the Firebase console shows it:
    `const firebaseConfig = { apiKey: "…", … };` (unquoted keys, trailing commas)."""
    text = (raw or "").strip()
    if not text:
        return None
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    body = text[start:end + 1]
    body = re.sub(r"//[^\n]*", "", body)                                  # comments
    body = re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', body)   # quote keys
    body = re.sub(r",\s*}", "}", body)                                    # trailing comma
    try:
        cfg = json.loads(body)
    except ValueError:
        return None
    return {k: str(cfg[k]) for k in FIELDS if cfg.get(k)}


def web_config():
    """The Firebase web-app config, or None if it's missing or incomplete."""
    raw = current_app.config.get("FIREBASE_WEB_CONFIG") or ""
    if not raw:
        return None
    cfg = parse_web_config(raw)
    if not cfg or not all(cfg.get(k) for k in ("apiKey", "projectId", "appId")):
        current_app.logger.warning("FIREBASE_WEB_CONFIG couldn't be read (it needs apiKey, projectId and appId).")
        return None
    return cfg


def analytics_config():
    """The config, when it includes Google Analytics (a measurementId)."""
    cfg = web_config()
    return cfg if cfg and cfg.get("measurementId") else None


def google_signin_config():
    """The config, when Google sign-in can work (it needs the auth domain)."""
    cfg = web_config()
    return cfg if cfg and cfg.get("authDomain") else None


def consent():
    v = request.cookies.get(COOKIE)
    return v if v in CHOICES else None


def enabled_here():
    """Analytics may load on this page (if the visitor consents): configured, and not the admin area."""
    if request.path.startswith("/admin") or (g.get("user") and g.user["role"] == "admin"):
        return False
    return analytics_config() is not None


def track(name, **params):
    """Queue an analytics event for the next page view (sent only if the visitor allowed analytics)."""
    events = session.get("_events", [])[-9:]
    events.append({"name": name, "params": params})
    session["_events"] = events


def pending_events():
    return session.pop("_events", []) if "_events" in session else []
