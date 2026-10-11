"""Every string marked for translation must have an Arabic translation."""
import os
import re
import unittest

from locumdoc import refdata
from locumdoc.translations.ar import AR

ROOT = os.path.join(os.path.dirname(__file__), "..", "locumdoc")
# _('...') or _("...") with the usual escapes; the first argument only.
PATTERN = re.compile(r"""\b_\(\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")""")
SKIP_DIRS = {os.path.join("templates", "admin"), os.path.join("templates", "email")}
SKIP_FILES = {os.path.join("views", "admin.py"), "i18n.py"}


def msgids():
    found = {}
    for base, _dirs, files in os.walk(ROOT):
        rel_dir = os.path.relpath(base, ROOT)
        if any(rel_dir.startswith(d) for d in SKIP_DIRS):
            continue
        for name in files:
            if not name.endswith((".py", ".html", ".txt")):
                continue
            rel = os.path.normpath(os.path.join(rel_dir, name))
            if rel in SKIP_FILES or rel.startswith("translations"):
                continue
            with open(os.path.join(base, name), encoding="utf8") as fh:
                for m in PATTERN.finditer(fh.read()):
                    raw = m.group(1) if m.group(1) is not None else m.group(2)
                    found.setdefault(raw.encode().decode("unicode_escape").encode("latin-1").decode("utf8"), rel)
    # Data shown through _() dynamically
    for options in (refdata.GRADES, refdata.QATAR_LICENSE_STATUS, refdata.EXAM_STATUS, refdata.DOCUMENT_KINDS,
                    refdata.FACILITY_TYPES, refdata.SECTORS, refdata.RATE_PERIODS, refdata.APPLICATION_STATUSES,
                    refdata.JOB_STATUSES):
        for _k, v in options:
            found.setdefault(v, "refdata")
    for name in refdata.SPECIALTIES:
        found.setdefault(name, "specialties")
    for c in refdata.COUNTRIES:
        found.setdefault(c[1], "countries")
        found.setdefault(c[4], "licensing bodies")
    for cities in refdata.CITIES.values():
        for city in cities:
            found.setdefault(city, "cities")
    # Email subjects (passed to mail.send as message ids) and other dynamic strings
    for t in ("Dr", "Prof", "Mr", "Ms", "Your session expired. Reload the page and try again.",
              "Reload the page and try again.", "Find locum jobs", "Rate on request",
              "Welcome to LocumDoc", "Your LocumDoc facility account", "Reset your LocumDoc password",
              "New applicant: %(title)s", "Application sent: %(title)s", "Dr %(name)s accepted your invitation",
              "Dr %(name)s declined your invitation", "Update on your application: %(title)s",
              "%(facility)s invited you to a locum role", "Your LocumDoc profile is verified",
              "Your facility is verified on LocumDoc"):
        found.setdefault(t, "misc")
    return found


class ArabicCoverage(unittest.TestCase):
    def test_every_string_translated(self):
        missing = {k: v for k, v in msgids().items() if k not in AR}
        self.assertEqual(missing, {}, "Untranslated strings:\n" + "\n".join(f"{v}: {k}" for k, v in missing.items()))

    def test_placeholders_match(self):
        ph = re.compile(r"%\(\w+\)s")
        for en, ar in AR.items():
            self.assertEqual(sorted(ph.findall(en)), sorted(ph.findall(ar)), f"Placeholder mismatch: {en!r}")


if __name__ == "__main__":
    unittest.main()
