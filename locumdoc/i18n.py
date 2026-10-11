"""Lightweight translation layer (English source strings, Arabic catalogue).

Usage in Python and templates:  _("Find locum jobs")  or  _("Hello %(name)s", name=x)
Untranslated strings fall back to English, and tests/test_i18n.py fails if any
string marked with _() is missing from the Arabic catalogue.
"""
from datetime import date, datetime

from flask import g, request

from .translations.ar import AR

LANGUAGES = {"en": {"name": "English", "dir": "ltr"}, "ar": {"name": "العربية", "dir": "rtl"}}
DEFAULT = "en"
COOKIE = "lang"

CATALOGS = {"ar": AR}

AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر",
             "أكتوبر", "نوفمبر", "ديسمبر"]

CURRENCY_AR = {"QAR": "ر.ق", "AED": "د.إ", "SAR": "ر.س", "KWD": "د.ك", "OMR": "ر.ع", "BHD": "د.ب"}


def current():
    return g.get("lang_override") or g.get("lang") or DEFAULT


def gettext(message, **kwargs):
    lang = current()
    text = CATALOGS.get(lang, {}).get(message, message) if lang != "en" else message
    return text % kwargs if kwargs else text


_ = gettext


def direction():
    return LANGUAGES[current()]["dir"]


def detect(user=None):
    """Pick the language for this request: explicit cookie, then account preference, then browser."""
    if request.path.startswith("/admin"):
        return "en"  # the admin panel is English-only
    cookie = request.cookies.get(COOKIE)
    if cookie in LANGUAGES:
        return cookie
    if user is not None and user["lang"] in LANGUAGES:
        return user["lang"]
    return request.accept_languages.best_match(list(LANGUAGES), default=DEFAULT) or DEFAULT


class override:
    """Render something (an email) in a given language: `with override('ar'): ...`."""

    def __init__(self, lang):
        self.lang = lang if lang in LANGUAGES else DEFAULT

    def __enter__(self):
        self.prev = g.get("lang_override")
        g.lang_override = self.lang

    def __exit__(self, *exc):
        g.lang_override = self.prev


# ------------------------------------------------------------------ formatting

def format_date(value, with_year=True):
    if not value:
        return "—"
    try:
        d = datetime.fromisoformat(str(value)[:19]) if not isinstance(value, (date, datetime)) else value
    except ValueError:
        return value
    if current() == "ar":
        out = f"{d.day} {AR_MONTHS[d.month - 1]}"
    else:
        out = d.strftime("%-d %b")
    return f"{out} {d.year}" if with_year else out


def format_money(amount, currency="QAR"):
    if amount in (None, ""):
        return _("Rate on request")
    if current() == "ar":
        return f"{int(amount):,} {CURRENCY_AR.get(currency, currency)}"
    return f"{currency} {int(amount):,}"


def count_noun(n, en_one, en_many, ar_forms):
    """Number + noun with correct plural. ar_forms = (one, two, few (3-10), many (11+))."""
    n = int(n)
    if current() != "ar":
        return f"{n} {en_one if n == 1 else en_many}"
    one, two, few, many = ar_forms
    if n == 1:
        return one
    if n == 2:
        return two
    if 3 <= n % 100 <= 10:
        return f"{n} {few}"
    return f"{n} {many}"


def weeks(n):
    return count_noun(n, "week", "weeks", ("أسبوع واحد", "أسبوعان", "أسابيع", "أسبوعًا"))


def years(n):
    return count_noun(n, "year", "years", ("سنة واحدة", "سنتان", "سنوات", "سنة"))
