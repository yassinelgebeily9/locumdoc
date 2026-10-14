"""Where LocumDoc keeps its records.

In production this is Google Cloud Firestore, the database behind Firebase. Every record
(a user, a doctor profile, a job, an application...) is a Firestore document in a
collection named after its kind, with a string id.

Without a Firebase project (on your Mac, and in the tests) the same records are kept by
LocalBackend: in memory, and saved to `instance/localstore.json` so they survive restarts.

Views never talk to a backend directly. They call the functions at the bottom of this
module: get, find, add, update, delete... which also keep a small per-request cache so a
page that looks up the same specialty or facility ten times reads it once.
"""
import fcntl
import hashlib
import json
import os
import re
import secrets
import string
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import current_app, g, has_app_context

NOW = object()  # placeholder in DEFAULTS: filled with the current time when a record is created

# Every field a record of each kind has, with its default. Mirrors the old SQL schema, so a
# record read from either backend always has the same shape.
DEFAULTS = {
    "countries": {"code": "", "name": "", "slug": "", "currency": "", "licensing_body": "", "active": 0,
                  "sort_order": 100},
    "cities": {"country_id": "", "name": ""},
    "specialties": {"name": "", "slug": ""},
    "users": {"email": "", "password_hash": "", "role": "", "is_active": 1, "lang": "en", "created_at": NOW,
              "google_uid": None, "email_verified": 0,
              "last_login_at": None},
    "doctors": {"user_id": "", "title": "Dr", "first_name": "", "last_name": "", "phone": "", "nationality": "",
                "current_country": "", "specialty_id": None, "subspecialty": "", "grade": "", "academic_rank": "",
                "years_experience": None, "qualifications": "", "medical_school": "", "graduation_year": None,
                "primary_license": "", "qatar_license_status": "none", "has_psv": 0, "exam_status": "unknown",
                "good_standing": 0, "languages": "", "available_from": None, "available_to": None,
                "min_weeks": None, "preferred_countries": "QA", "bio": "", "visible_to_facilities": 1,
                "verified": 0, "admin_notes": "", "updated_at": NOW},
    "facilities": {"user_id": "", "name": "", "facility_type": "hospital", "country_id": None, "city_id": None,
                   "sector": "private", "website": "", "contact_name": "", "contact_role": "", "phone": "",
                   "about": "", "verified": 0, "admin_notes": "", "updated_at": NOW},
    "documents": {"user_id": "", "kind": "", "original_name": "", "storage_name": "", "mime_type": "",
                  "size_bytes": 0, "created_at": NOW},
    "jobs": {"facility_id": "", "title": "", "specialty_id": "", "grade": "", "country_id": "", "city_id": None,
             "start_date": "", "end_date": "", "rate_amount": None, "rate_currency": "QAR", "rate_period": "month",
             "show_rate": 0,
             "accommodation": 0, "flights": 0, "transport": 0, "licensing_support": 0, "description": "",
             "requirements": "", "status": "open", "created_at": NOW, "updated_at": NOW},
    "applications": {"job_id": "", "doctor_id": "", "cover_note": "", "status": "submitted", "created_at": NOW,
                     "updated_at": NOW},
    "invitations": {"facility_id": "", "doctor_id": "", "job_id": None, "message": "", "status": "sent",
                    "created_at": NOW},
    "enquiries": {"name": "", "email": "", "organisation": "", "message": "", "created_at": NOW},
    # One record per email address, keyed by its hash: makes "one account per email" atomic.
    "emails": {"user_id": ""},
}

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_ID_CHARS = string.ascii_letters + string.digits


def now():
    """UTC timestamp as text. Sorts correctly as a string; microseconds keep same-second records in order."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S.%f")


def valid_id(doc_id):
    return isinstance(doc_id, str) and bool(_ID_RE.match(doc_id)) and not doc_id.startswith("__")


def email_key(email):
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


def with_defaults(coll, data):
    out = {}
    for k, v in DEFAULTS.get(coll, {}).items():
        out[k] = now() if v is NOW else v
    out.update(data)
    out.pop("id", None)
    return out


# ------------------------------------------------------------------ backends

class LocalBackend:
    """Records in memory, optionally saved to a JSON file. Safe across processes on one machine."""

    def __init__(self, path=None):
        self.path = path
        self.data = {}
        self.mtime = None
        self.lock = threading.RLock()
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            self._reload()

    # file handling
    def _reload(self):
        if not self.path:
            return
        try:
            m = os.stat(self.path).st_mtime_ns
        except FileNotFoundError:
            return
        if m != self.mtime:
            with open(self.path, encoding="utf8") as fh:
                self.data = json.load(fh)
            self.mtime = m

    def _mutate(self, fn):
        with self.lock:
            if not self.path:
                return fn()
            with open(self.path + ".lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                try:
                    self._reload()
                    result = fn()
                    tmp = self.path + ".tmp"
                    with open(tmp, "w", encoding="utf8") as fh:
                        json.dump(self.data, fh, ensure_ascii=False, indent=1, sort_keys=True)
                    os.replace(tmp, self.path)
                    self.mtime = os.stat(self.path).st_mtime_ns
                    return result
                finally:
                    fcntl.flock(lk, fcntl.LOCK_UN)

    def _read(self):
        with self.lock:
            self._reload()

    # API
    def new_id(self, coll):
        return "".join(secrets.choice(_ID_CHARS) for _ in range(20))

    def get(self, coll, doc_id):
        self._read()
        d = self.data.get(coll, {}).get(doc_id)
        return dict(d) if d is not None else None

    def query(self, coll, filters):
        self._read()
        out = []
        for doc_id, d in self.data.get(coll, {}).items():
            if all(d.get(k) == v for k, v in filters.items()):
                out.append(dict(d, id=doc_id))
        return out

    def set(self, coll, doc_id, data):
        def fn():
            self.data.setdefault(coll, {})[doc_id] = dict(data)
        self._mutate(fn)

    def create(self, coll, doc_id, data):
        def fn():
            docs = self.data.setdefault(coll, {})
            if doc_id in docs:
                return False
            docs[doc_id] = dict(data)
            return True
        return self._mutate(fn)

    def update(self, coll, doc_id, fields):
        def fn():
            d = self.data.get(coll, {}).get(doc_id)
            if d is None:
                return False
            d.update(fields)
            return True
        return self._mutate(fn)

    def delete(self, coll, doc_id):
        def fn():
            self.data.get(coll, {}).pop(doc_id, None)
        self._mutate(fn)


class FirestoreBackend:
    """Google Cloud Firestore (Firebase). Needs FIREBASE_PROJECT_ID and a service account."""

    def __init__(self, project, credentials_info=None, database=None):
        self.project, self.credentials_info, self.database = project, credentials_info, database
        self._client, self._pid = None, None

    @property
    def client(self):
        # Made per process: gunicorn forks workers, and a Firestore connection must not cross a fork.
        if self._client is None or self._pid != os.getpid():
            from google.cloud import firestore
            from google.oauth2 import service_account

            info = self.credentials_info
            creds = service_account.Credentials.from_service_account_info(info) if info else None
            kwargs = {"project": self.project, "credentials": creds}
            if self.database:
                kwargs["database"] = self.database
            self._client, self._pid = firestore.Client(**kwargs), os.getpid()
        return self._client

    def _ref(self, coll, doc_id):
        return self.client.collection(coll).document(doc_id)

    def new_id(self, coll):
        return self.client.collection(coll).document().id

    def get(self, coll, doc_id):
        snap = self._ref(coll, doc_id).get()
        return snap.to_dict() if snap.exists else None

    def query(self, coll, filters):
        from google.cloud.firestore_v1.base_query import FieldFilter

        # Firestore filters on one field (always served by its automatic single-field index, so no
        # composite indexes need setting up); any other conditions are checked here.
        items = list(filters.items())
        q = self.client.collection(coll)
        if items:
            q = q.where(filter=FieldFilter(items[0][0], "==", items[0][1]))
        rows = (dict(s.to_dict(), id=s.id) for s in q.stream())
        return [r for r in rows if all(r.get(k) == v for k, v in items[1:])]

    def set(self, coll, doc_id, data):
        self._ref(coll, doc_id).set(data)

    def create(self, coll, doc_id, data):
        from google.api_core.exceptions import Conflict

        try:
            self._ref(coll, doc_id).create(data)
            return True
        except Conflict:
            return False

    def update(self, coll, doc_id, fields):
        from google.api_core.exceptions import NotFound

        try:
            self._ref(coll, doc_id).update(fields)
            return True
        except NotFound:
            return False

    def delete(self, coll, doc_id):
        self._ref(coll, doc_id).delete()


def backend_from_config(config):
    """Firestore when a Firebase project is configured, otherwise the local JSON store."""
    project = config.get("FIREBASE_PROJECT_ID")
    if project and config.get("DATA_BACKEND", "firestore") != "local":
        info = config.get("FIREBASE_CREDENTIALS_JSON")
        return FirestoreBackend(project, json.loads(info) if info else None, config.get("FIRESTORE_DATABASE") or None)
    return LocalBackend(config.get("LOCAL_STORE_PATH"))


def init_app(app):
    app.extensions["store"] = backend_from_config(app.config)


# ------------------------------------------------- functions the views call

def _backend():
    return current_app.extensions["store"]


# Small reference lists every page needs. Kept for a minute per process so a page view doesn't
# re-read ~60 documents from Firestore; changes made in this process show immediately.
SHARED = {"countries", "cities", "specialties"}
SHARED_TTL = 60


def _shared(coll):
    cache = current_app.extensions.setdefault("store_shared", {})
    hit = cache.get(coll)
    if hit and time.monotonic() - hit[0] < SHARED_TTL:
        return hit[1]
    rows = _backend().query(coll, {})
    cache[coll] = (time.monotonic(), rows)
    return rows


def _cache():
    if not has_app_context():
        return None
    if "_store_cache" not in g:
        g._store_cache = {"docs": {}, "queries": {}}
    return g._store_cache


def _forget(coll, doc_id=None):
    if coll in SHARED and has_app_context():
        current_app.extensions.get("store_shared", {}).pop(coll, None)
    c = _cache()
    if c is None:
        return
    if doc_id is not None:
        c["docs"].pop((coll, doc_id), None)
    for key in [k for k in c["queries"] if k[0] == coll]:
        del c["queries"][key]


def get(coll, doc_id):
    """One record by id, or None. Ids from URLs are checked before they reach the database."""
    if doc_id is None:
        return None
    doc_id = str(doc_id)
    if not valid_id(doc_id):
        return None
    if coll in SHARED and has_app_context():
        return next((dict(r) for r in _shared(coll) if r["id"] == doc_id), None)
    c = _cache()
    key = (coll, doc_id)
    if c is not None and key in c["docs"]:
        d = c["docs"][key]
    else:
        d = _backend().get(coll, doc_id)
        if d is not None:
            d = dict(d, id=doc_id)
        if c is not None:
            c["docs"][key] = d
    return dict(d) if d is not None else None


def find(coll, **filters):
    """Every record whose fields equal the given values (no filters: the whole collection)."""
    c = _cache()
    key = (coll, tuple(sorted(filters.items(), key=lambda kv: kv[0])))
    if coll in SHARED and has_app_context():
        return [dict(r) for r in _shared(coll) if all(r.get(k) == v for k, v in filters.items())]
    if c is not None and key in c["queries"]:
        rows = c["queries"][key]
    else:
        rows = _backend().query(coll, filters)
        if c is not None:
            c["queries"][key] = rows
            for r in rows:
                c["docs"][(coll, r["id"])] = r
    return [dict(r) for r in rows]


def first(coll, **filters):
    rows = find(coll, **filters)
    return rows[0] if rows else None


def count(coll, **filters):
    return len(find(coll, **filters))


def add(coll, data, doc_id=None):
    """Create a record with every default filled in. Returns its id."""
    doc_id = str(doc_id) if doc_id is not None else _backend().new_id(coll)
    _backend().set(coll, doc_id, with_defaults(coll, data))
    _forget(coll, doc_id)
    return doc_id


def create(coll, doc_id, data, defaults=True):
    """Create only if no record has this id yet. Returns False if one already exists."""
    ok = _backend().create(coll, str(doc_id), with_defaults(coll, data) if defaults else dict(data))
    _forget(coll, str(doc_id))
    return ok


def update(coll, doc_id, **fields):
    if doc_id is None or not valid_id(str(doc_id)):
        return False
    fields.pop("id", None)
    ok = _backend().update(coll, str(doc_id), fields)
    _forget(coll, str(doc_id))
    return ok


def delete(coll, doc_id):
    if doc_id is None or not valid_id(str(doc_id)):
        return
    _backend().delete(coll, str(doc_id))
    _forget(coll, str(doc_id))


def delete_where(coll, **filters):
    for r in find(coll, **filters):
        delete(coll, r["id"])
