import os
from datetime import date, timedelta

from flask import Flask, g, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db, i18n, refdata, security, storage, store, world


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
        DATA_BACKEND=os.environ.get("DATA_BACKEND", "firestore"),
        LOCAL_STORE_PATH=os.environ.get("LOCAL_STORE_PATH", os.path.join(data_dir, "localstore.json")),
        LEGACY_SQLITE_PATH=os.path.join(data_dir, "locumdoc.sqlite3"),  # imported once by the local store
        UPLOAD_DIR=os.environ.get("UPLOAD_DIR", os.path.join(data_dir, "uploads")),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        SITE_URL=os.environ.get("SITE_URL", "http://localhost:5000").rstrip("/"),
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
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
            "font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'",
        )
        if app.config["SESSION_COOKIE_SECURE"]:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if g.get("user") is not None:
            resp.headers.setdefault("Cache-Control", "private, no-store")
        return resp

    # ------------------------------------------------------------ templates
    @app.context_processor
    def _ctx():
        return {
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
    @app.errorhandler(413)
    def _err(e):
        _ = i18n.gettext
        messages = {
            400: (_("Request not accepted"), _(getattr(e, "description", "") or "Reload the page and try again.")),
            403: (_("No access"), _("This page belongs to a different type of account.")),
            404: (_("Page not found"), _("The link may be out of date, or the job may have closed.")),
            413: (_("File too large"), _("Uploads can be up to %(mb)s MB.", mb=app.config["MAX_CONTENT_LENGTH"] // 1048576)),
        }
        title, text = messages.get(e.code, (_("Something went wrong"), ""))
        return render_template("public/error.html", code=e.code, title=title, text=text), e.code

    return app
