"""Outgoing email. Uses SMTP when configured, otherwise writes messages to the log.

Each email is rendered in the recipient's language: templates live in
templates/email/<name>.txt (English) and templates/email/ar/<name>.txt (Arabic).
"""
import smtplib
import ssl
import threading
from email.message import EmailMessage

from flask import current_app, render_template

from . import i18n


def send(to, subject, template, lang="en", subject_args=None, **ctx):
    """Send `template` to `to`. `subject` is an English message id, translated into `lang`."""
    if not to:
        return
    app = current_app._get_current_object()
    ctx.setdefault("site_url", app.config["SITE_URL"])
    with i18n.override(lang):
        subject_text = i18n.gettext(subject, **(subject_args or {}))
        names = [f"email/{lang}/{template}.txt", f"email/{template}.txt"] if lang != "en" else [f"email/{template}.txt"]
        body = render_template(app.jinja_env.select_template(names), **ctx)
    msg = EmailMessage()
    msg["Subject"] = subject_text
    msg["From"] = app.config["MAIL_FROM"]
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
    msg.set_content(body)

    if app.config.get("TESTING"):
        app.extensions.setdefault("outbox", []).append(msg)
        return
    if not app.config.get("SMTP_HOST"):
        app.logger.info("Email (SMTP not configured)\nTo: %s\nSubject: %s\n\n%s", msg["To"], subject_text, body)
        return
    threading.Thread(target=_deliver, args=(app, msg), daemon=True).start()


def notify_admin(subject, template, subject_args=None, **ctx):
    send(current_app.config.get("ADMIN_NOTIFY_EMAIL"), subject, template, "en", subject_args, **ctx)


def _deliver(app, msg):
    cfg = app.config
    try:
        if cfg.get("SMTP_SSL"):
            server = smtplib.SMTP_SSL(cfg["SMTP_HOST"], cfg["SMTP_PORT"], context=ssl.create_default_context(), timeout=20)
        else:
            server = smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=20)
            server.starttls(context=ssl.create_default_context())
        with server:
            if cfg.get("SMTP_USER"):
                server.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            server.send_message(msg)
    except Exception:  # noqa: BLE001 - never crash a request over email
        app.logger.exception("Email delivery failed: %s", msg["Subject"])
