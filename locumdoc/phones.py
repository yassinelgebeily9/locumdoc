"""Phone numbers: a country-code dropdown plus the number, checked with Google's libphonenumber.

Numbers are stored in the international E.164 form (+97455123456) and shown formatted
(+974 5512 3456). The check knows each country's real numbering plan, so a Qatari number
must be 8 digits starting with a valid prefix, a UK mobile 07xxx xxxxxx, and so on.
"""
import phonenumbers as pn

from . import world

# Gulf first (where the jobs are), then the countries most doctors come from.
FIRST = ["QA", "SA", "AE", "KW", "OM", "BH"]
_CODE_BY_NAME = {name: code for code, name in world.WORLD}
COMMON = FIRST + [_CODE_BY_NAME[n] for n in world.COMMON if _CODE_BY_NAME.get(n) and _CODE_BY_NAME[n] not in FIRST]
NAMES = {code: name for code, name in world.WORLD}


def dial_code(region):
    return pn.country_code_for_region(region or "")


def code_for_country(name, default="QA"):
    """ISO code for a stored country name ("United Kingdom" -> "GB")."""
    code = _CODE_BY_NAME.get(name or "")
    return code if code and dial_code(code) else default


def _label(region, gettext):
    return f"+{dial_code(region)} {gettext(NAMES[region])}"


def options(gettext):
    """(common, everything) as lists of (ISO code, label) for the country-code dropdown."""
    usable = [c for c, _n in world.WORLD if dial_code(c)]
    common = [(c, _label(c, gettext)) for c in COMMON if c in usable]
    everything = sorted(((c, _label(c, gettext)) for c in usable),
                        key=lambda x: world._sort_key(gettext(NAMES[x[0]])))
    return common, everything


class PhoneError(ValueError):
    pass


def normalise(region, raw):
    """Check a number typed with its country code; returns (E.164 string, region). Raises PhoneError."""
    raw = (raw or "").strip()
    region = (region or "").strip().upper()
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    if not raw.startswith("+") and not dial_code(region):
        raise PhoneError("country")
    try:
        num = pn.parse(raw, None if raw.startswith("+") else region)
    except pn.NumberParseException:
        raise PhoneError("invalid")
    if not pn.is_valid_number(num):
        raise PhoneError("invalid")
    return pn.format_number(num, pn.PhoneNumberFormat.E164), pn.region_code_for_number(num)


def parts(value, region=None, default="QA"):
    """For filling the form again: (country code, number as people write it locally)."""
    value = (value or "").strip()
    if region and value and not value.startswith("+"):  # what the person just typed, shown back with an error
        return region, value
    if value:
        try:
            num = pn.parse(value, None if value.startswith("+") else (region or default))
            r = pn.region_code_for_number(num)
            if r and dial_code(r):
                return r, pn.format_number(num, pn.PhoneNumberFormat.NATIONAL)
        except pn.NumberParseException:
            pass
    return (region or default), value


def display(value):
    """+97455123456 -> "+974 5512 3456". Anything unreadable is shown as stored."""
    if not value:
        return ""
    try:
        num = pn.parse(value, None)
        if pn.is_possible_number(num):
            return pn.format_number(num, pn.PhoneNumberFormat.INTERNATIONAL)
    except pn.NumberParseException:
        pass
    return value


def tel_link(value):
    """Value for a tel: link."""
    try:
        return pn.format_number(pn.parse(value, None), pn.PhoneNumberFormat.E164)
    except pn.NumberParseException:
        return "".join(ch for ch in (value or "") if ch.isdigit() or ch == "+")
