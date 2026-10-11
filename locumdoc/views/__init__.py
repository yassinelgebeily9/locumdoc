"""Shared helpers for view modules."""
import re
from datetime import date

from flask import request

from ..i18n import _

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Form:
    """Tiny form helper: reads request.form, collects errors per field."""

    def __init__(self, data=None):
        self.data = data if data is not None else request.form
        self.errors = {}
        self.clean = {}

    def text(self, name, required=False, max_len=500, label=None):
        v = (self.data.get(name) or "").strip()
        if required and not v:
            self.errors[name] = _("Enter %(label)s.", label=label or name.replace("_", " "))
        elif len(v) > max_len:
            self.errors[name] = _("Keep this under %(n)s characters.", n=max_len)
        self.clean[name] = v
        return v

    def email(self, name="email"):
        v = (self.data.get(name) or "").strip().lower()
        if not EMAIL_RE.match(v):
            self.errors[name] = _("Enter a valid email address.")
        self.clean[name] = v
        return v

    def choice(self, name, options, required=True, label=None):
        v = (self.data.get(name) or "").strip()
        keys = [str(k) for k, _lbl in options]
        if v not in keys:
            if required or v:
                self.errors[name] = _("Choose %(label)s.", label=label or name.replace("_", " "))
            v = ""
        self.clean[name] = v
        return v

    def integer(self, name, required=False, min_v=None, max_v=None, label=None):
        raw = (self.data.get(name) or "").replace(",", "").strip()
        if not raw:
            if required:
                self.errors[name] = _("Enter %(label)s.", label=label or name.replace("_", " "))
            self.clean[name] = None
            return None
        try:
            v = int(raw)
        except ValueError:
            self.errors[name] = _("Enter a whole number.")
            self.clean[name] = None
            return None
        if (min_v is not None and v < min_v) or (max_v is not None and v > max_v):
            self.errors[name] = _("Enter a number between %(min)s and %(max)s.", min=min_v, max=max_v)
        self.clean[name] = v
        return v

    def date(self, name, required=False, label=None):
        raw = (self.data.get(name) or "").strip()
        if not raw:
            if required:
                self.errors[name] = _("Choose %(label)s.", label=label or name.replace("_", " "))
            self.clean[name] = None
            return None
        try:
            v = date.fromisoformat(raw).isoformat()
        except ValueError:
            self.errors[name] = _("Enter a date as YYYY-MM-DD.")
            v = None
        self.clean[name] = v
        return v

    def flag(self, name):
        v = 1 if self.data.get(name) in ("1", "on", "yes", "true") else 0
        self.clean[name] = v
        return v

    @property
    def ok(self):
        return not self.errors


def page_args(per_page=20):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    return page, per_page, (page - 1) * per_page
