"""Text helpers. The site is English-only.

Templates and views still mark text with _("...") / _("Hello %(name)s", name=x): it fills in the
values and returns the English text, and keeps every string in one recognisable form should a
second language ever be added again. (The Arabic interface removed on 13 Oct 2026 is preserved on
the `arabic-archive` branch.)
"""
from contextlib import contextmanager
from datetime import date, datetime

LANGUAGES = {"en": {"name": "English", "dir": "ltr"}}
DEFAULT = "en"


def current():
    return DEFAULT


def gettext(message, **kwargs):
    return message % kwargs if kwargs else message


_ = gettext


def direction():
    return "ltr"


@contextmanager
def override(_lang):
    """Kept so email code reads the same; everything renders in English."""
    yield


# ------------------------------------------------------------------ formatting

def format_date(value, with_year=True):
    if not value:
        return "—"
    try:
        d = datetime.fromisoformat(str(value)[:19]) if not isinstance(value, (date, datetime)) else value
    except ValueError:
        return value
    out = d.strftime("%-d %b")
    return f"{out} {d.year}" if with_year else out


def format_money(amount, currency="QAR"):
    if amount in (None, ""):
        return "Rate on request"
    return f"{currency} {int(amount):,}"


def _count(n, one, many):
    n = int(n)
    return f"{n} {one if n == 1 else many}"


def weeks(n):
    return _count(n, "week", "weeks")


def years(n):
    return _count(n, "year", "years")
