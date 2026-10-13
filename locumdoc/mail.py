"""Outgoing email. Uses SMTP when configured, otherwise writes messages to the log.

Templates live in templates/email/<name>.txt.
"""
import smtplib
import ssl
import threading
from email.message import EmailMessage

from flask import current_app, render_template

from . import i18n


def send(to, subject, template, lang="en", subject_args=None, **ctx):
    """Send `template` to `to`. `lang` is accepted for older callers; every email is English."""
    if not to:
        return
    app = current_app._get_current_object()
    ctx.setdefault("site_url", app.config["SITE_URL"])
    subject_text = i18n.gettext(subject, **(subject_args or {}))
    body = render_template(f"email/{template}.txt", **ctx)
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
