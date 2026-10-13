"""Sign in with Google, through Firebase Authentication.

The browser does the Google pop-up with the Firebase SDK and sends us the resulting Firebase
ID token. We check that token with Google's public keys (signature, project, issuer, expiry) and
only then trust the email address in it. Firebase keeps no session of its own: the website's
normal login session takes over from there.
"""
from flask import current_app


class InvalidToken(ValueError):
    pass


_transport = None


def verify(token, project_id):
    """Return the token's claims if it's a valid Google sign-in for this Firebase project."""
    global _transport
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    if not token or len(token) > 4096:
        raise InvalidToken("missing")
    if _transport is None:
        _transport = google_requests.Request()
    try:
        claims = id_token.verify_firebase_token(token, _transport, audience=project_id)
    except Exception as e:  # expired, wrong project, bad signature, network...
        current_app.logger.info("Google sign-in token rejected: %s", e)
        raise InvalidToken(str(e)) from e
    if not claims or claims.get("iss") != f"https://securetoken.google.com/{project_id}":
        raise InvalidToken("issuer")
    if (claims.get("firebase") or {}).get("sign_in_provider") != "google.com":
        raise InvalidToken("provider")
    if not claims.get("email") or not claims.get("email_verified"):
        raise InvalidToken("email not verified")
    return claims


def split_name(full):
    parts = (full or "").strip().split()
    return (parts[0], " ".join(parts[1:])) if parts else ("", "")
