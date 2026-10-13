import os
from datetime import date, timedelta

from flask import Flask, g, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import analytics, db, i18n, phones, refdata, security, storage, store, world


def _site_url(v):
    """The public address, always with a scheme: "locumdoc.me" becomes "https://locumdoc.me"."""
    v = (v or "http://localhost:5000").strip().rstrip("/")
    return v if v.startswith(("http://", "https://")) else "https://" + v


def _bool(v):
    return str(v).lower() in ("1", "true", "yes", "on")


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    data_dir = os.environ.get("DATA_DIR", app.instance_path)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        # Firebase: set FIREBASE_PROJECT_ID (+ FIREBASE_STORAGE_BUCKET and FIREBASE_CREDENTIALS_JSON) to keep
        # records in Firestore and PDFs in Firebase Storage. Without them, everything stays in DATA_DIR.
        FIREBASE_PROJECT_ID=os.environ.get("FIREBASE_PROJECT_ID", ""),
        FIREBASE_STORAGE_BUCKET=os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        FIREBASE_CREDENTIALS_JSON=os.environ.get("FIREBASE_CREDENTIALS_JSON", ""),
        FIRESTORE_DATABASE=os.environ.get("FIRESTORE_DATABASE", ""),
        # Firebase Analytics: the web-app config from the Firebase console, as JSON (public values).
        FIREBASE_WEB_CONFIG=os.environ.get("FIREBASE_WEB_CONFIG", ""),
        DATA_BACKEND=os.environ.get("DATA_BACKEND", "firestore"),
        LOCAL_STORE_PATH=os.environ.get("LOCAL_STORE_PATH", os.path.join(data_dir, "localstore.json")),
        LEGACY_SQLITE_PATH=os.path.join(data_dir, "locumdoc.sqlite3"),  # imported once by the local store
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", os.path.join(data_dir, "uploads")),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        SITE_URL=_site_url(os.environ.get("SITE_URL")),
        MAIL_FROM=os.environ.get("MAIL_FROM", "LocumDoc <hello@locumdoc.me>"),
        ADMIN_NOTIFY_EMAIL=os.environ.get("ADMIN_NOTIFY_EMAIL", ""),
        CONTACT_EMAIL=os.environ.get("CONTACT_EMAIL", "hello@locumdoc.me"),
        SMTP_HOST=os.environ.get("SMTP_HOST", ""),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", "587")),
        SMTP_USER=os.environ.get("SMTP_USER", ""),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
        SMTP_SSL=_bool(os.environ.get("SMTP_SSL", "0")),
        ADMIN_EMAIL=os.environ.get("ADMIN_EMAIL", ""),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        SEED_DEMO=_bool(os.environ.get("SEED_DEMO", "0")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_bool(os.environ.get("SECURE_COOKIES", "0")),
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
    )
    if test_config:
        app.config.update(test_config)

    if app.config["SECRET_KEY"] == "dev-only-change-me" and not app.debug and not app.config.get("TESTING"):
        app.logger.warning("SECRET_KEY is not set. Set it before going live.")

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    store.init_app(app)
    storage.init_app(app)
    db.register_cli(app)
    db.ensure_db(app)

    @app.before_request
    def _before():
        security.load_user()
        g.lang = i18n.detect(g.user)
        if not request.path.startswith("/static/"):
            security.check_csrf()

    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        a = analytics.web_config() is not None  # allow Google Analytics' hosts only when it's configured
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            f"img-src 'self' data:{' ' + analytics.CSP_IMG if a else ''}; "
            "style-src 'self'; "
            f"script-src 'self'{' ' + analytics.CSP_SCRIPT if a else ''}; "
            f"connect-src 'self'{' ' + analytics.CSP_CONNECT if a else ''}; "
            "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if g.get("user") is not None:
            resp.headers.setdefault("Cache-Control", "private, no-store")
        return resp

    # ------------------------------------------------------------ templates
    # Pages search engines shouldn't list: anything behind a login, one-off pages and errors.
    PRIVATE_BLUEPRINTS = {"doctor", "facility", "admin", "files"}
    PRIVATE_ENDPOINTS = {"auth.account", "auth.reset", "auth.forgot", "public.contact_thanks", "public.cookies"}

    @app.context_processor
    def _ctx():
        site = app.config["SITE_URL"]
        return {
            "site_url": site,
            "cookie_consent": analytics.consent(),
            "analytics_config": analytics.web_config() if analytics.enabled_here() else None,
            "analytics_events": analytics.pending_events,
            "canonical_url": site + request.path,
            "noindex": g.get("noindex") or request.blueprint in PRIVATE_BLUEPRINTS
                       or request.endpoint in PRIVATE_ENDPOINTS,
            "csrf_token": security.csrf_token,
            "current_user": g.get("user"),
            "ref": refdata,
            "label": refdata.label,
            "today": date.today().isoformat(),
            "contact_email": app.config["CONTACT_EMAIL"],
            "_": i18n.gettext,
            "lang": i18n.current(),
            "text_dir": i18n.direction(),
            "languages": i18n.LANGUAGES,
            "comma": "، " if i18n.current() == "ar" else ", ",
            "weeks_n": i18n.weeks,
            "country_options": lambda: world.options(i18n.gettext),
        "phone_country_options": lambda: phones.options(i18n.gettext, i18n.current() == "ar"),
        "phone_parts": phones.parts,
        "phone_code_for": phones.code_for_country,
            "currency_name": lambda code: i18n.CURRENCY_AR.get(code, code) if i18n.current() == "ar" else code,
        }

    @app.template_filter("d")
    def _fmt_date(value, fmt="%-d %b %Y"):
        return i18n.format_date(value, with_year="%Y" in fmt)

    @app.template_filter("money")
    def _money(amount, currency="QAR"):
        return i18n.format_money(amount, currency)

    @app.template_filter("weeks")
    def _weeks(row):
        try:
            s = date.fromisoformat(row["start_date"])
            e = date.fromisoformat(row["end_date"])
        except (TypeError, ValueError, KeyError):
            return ""
        return i18n.weeks(max(1, round((e - s).days / 7)))

    @app.template_filter("years")
    def _years(n):
        return "—" if n in (None, "") else i18n.years(n)

    app.add_template_filter(phones.display, "phone")
    app.add_template_filter(phones.tel_link, "tel")

    @app.template_filter("filesize")
    def _filesize(n):
        n = int(n or 0)
        return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{max(1, n // 1024)} KB"

    # ------------------------------------------------------------ blueprints
    from .views import admin, auth, doctor, facility, files, public

    for bp in (public.bp, auth.bp, doctor.bp, facility.bp, admin.bp, files.bp):
        app.register_blueprint(bp)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    @app.errorhandler(500)
    def _err(e):
        _ = i18n.gettext
        code = getattr(e, "code", 500) or 500
        if code == 500:
            app.logger.exception("Server error on %s", request.path, exc_info=getattr(e, "original_exception", e))
        messages = {
            400: (_("Request not accepted"), _(getattr(e, "description", "") or "Reload the page and try again.")),
            403: (_("No access"), _("This page belongs to a different type of account.")),
            404: (_("Page not found"), _("The link may be out of date, or the job may have closed.")),
            405: (_("Page not found"), _("The link may be out of date, or the job may have closed.")),
            413: (_("File too large"), _("Uploads can be up to %(mb)s MB.", mb=app.config["MAX_CONTENT_LENGTH"] // 1048576)),
            500: (_("Something went wrong on our side"),
                  _("Nothing you did caused this. Try again in a minute; if it keeps happening, email us and we'll fix it.")),
        }
        title, text = messages.get(code, (_("Something went wrong"), ""))
        g.noindex = True
        try:
            return render_template("public/error.html", code=code, title=title, text=text), code
        except Exception:  # never let the error page itself fail
            app.logger.exception("Error page failed")
            return f"<h1>{code}</h1><p>{title}</p>", code

    return app
