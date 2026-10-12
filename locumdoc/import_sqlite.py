"""One-off move from the old SQLite database (locumdoc.sqlite3 + uploads/) into the current store.

    flask --app wsgi import-sqlite instance/locumdoc.sqlite3

With FIREBASE_* settings present this fills Firestore and Firebase Storage; otherwise the
local store. Records keep their old numbers as ids (user 7 becomes "7"), so links still work.
Running it twice is safe: anything already there is left alone.
"""
import os
import sqlite3

from . import store
from .db import city_id_for, slugify
from .storage import _files

DEMONYMS = {
    "egyptian": "Egypt", "jordanian": "Jordan", "sudanese": "Sudan", "syrian": "Syria", "lebanese": "Lebanon",
    "palestinian": "Palestine", "iraqi": "Iraq", "yemeni": "Yemen", "tunisian": "Tunisia", "libyan": "Libya",
    "algerian": "Algeria", "moroccan": "Morocco", "qatari": "Qatar", "saudi": "Saudi Arabia",
    "emirati": "United Arab Emirates", "kuwaiti": "Kuwait", "omani": "Oman", "bahraini": "Bahrain",
    "indian": "India", "pakistani": "Pakistan", "bangladeshi": "Bangladesh", "sri lankan": "Sri Lanka",
    "filipino": "Philippines", "nigerian": "Nigeria", "british": "United Kingdom", "english": "United Kingdom",
    "scottish": "United Kingdom", "welsh": "United Kingdom", "irish": "Ireland", "american": "United States",
    "canadian": "Canada", "australian": "Australia", "south african": "South Africa", "turkish": "Turkey",
    "iranian": "Iran", "german": "Germany", "french": "France", "italian": "Italy", "spanish": "Spain",
    "greek": "Greece", "romanian": "Romania", "polish": "Poland", "ukrainian": "Ukraine", "russian": "Russia",
}


def _rows(conn, table):
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]  # table names are fixed above
    except sqlite3.OperationalError:
        return []


def _pick(coll, row, **override):
    out = {k: row[k] for k in store.DEFAULTS[coll] if k in row}
    out.update(override)
    return out


def run(sqlite_path, uploads=None):
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    uploads = uploads or os.path.join(os.path.dirname(os.path.abspath(sqlite_path)), "uploads")
    report = {}

    def done(kind, n=1):
        report[kind] = report.get(kind, 0) + n

    country = {}
    for c in _rows(conn, "countries"):
        country[c["id"]] = c["code"]
        if not store.create("countries", c["code"], _pick("countries", c)):
            store.update("countries", c["code"], active=c["active"])  # keep which countries were open
    city = {}
    for c in _rows(conn, "cities"):
        code = country.get(c["country_id"])
        if code:
            city[c["id"]] = city_id_for(code, c["name"])
            store.create("cities", city[c["id"]], {"country_id": code, "name": c["name"]})
    spec = {}
    for s in _rows(conn, "specialties"):
        spec[s["id"]] = slugify(s["name"])
        store.create("specialties", spec[s["id"]], {"name": s["name"], "slug": spec[s["id"]]})

    users = set()
    for u in _rows(conn, "users"):
        uid = str(u["id"])
        email = u["email"].strip().lower()
        if not store.create("emails", store.email_key(email), {"user_id": uid}, defaults=False):
            done("accounts skipped (email already registered)")
            continue
        store.add("users", _pick("users", u, email=email), doc_id=uid)
        users.add(uid)
        done("accounts")

    for d in _rows(conn, "doctors"):
        uid = str(d["user_id"])
        if uid in users:
            nat = DEMONYMS.get((d.get("nationality") or "").strip().lower(), d.get("nationality") or "")
            store.add("doctors", _pick("doctors", d, user_id=uid, specialty_id=spec.get(d["specialty_id"]),
                                       nationality=nat), doc_id=uid)
            done("doctor profiles")
    for f in _rows(conn, "facilities"):
        uid = str(f["user_id"])
        if uid in users:
            store.add("facilities", _pick("facilities", f, user_id=uid, country_id=country.get(f["country_id"]),
                                          city_id=city.get(f["city_id"])), doc_id=uid)
            done("facilities")

    for doc in _rows(conn, "documents"):
        uid = str(doc["user_id"])
        if uid not in users:
            continue
        path = os.path.join(uploads, os.path.basename(doc["storage_name"]))
        if not os.path.exists(path):
            done("files missing on disk")
            continue
        with open(path, "rb") as fh:
            _files().put(doc["storage_name"], fh.read(), doc["mime_type"])
        store.add("documents", _pick("documents", doc, user_id=uid), doc_id=str(doc["id"]))
        done("files")

    jobs = set()
    for j in _rows(conn, "jobs"):
        if str(j["facility_id"]) in users:
            store.add("jobs", _pick("jobs", j, facility_id=str(j["facility_id"]), specialty_id=spec.get(j["specialty_id"]),
                                    country_id=country.get(j["country_id"]), city_id=city.get(j["city_id"])),
                      doc_id=str(j["id"]))
            jobs.add(str(j["id"]))
            done("jobs")
    for a in _rows(conn, "applications"):
        jid, did = str(a["job_id"]), str(a["doctor_id"])
        if jid in jobs and did in users:
            store.create("applications", f"{jid}_{did}", _pick("applications", a, job_id=jid, doctor_id=did))
            done("applications")
    for i in _rows(conn, "invitations"):
        fid, did = str(i["facility_id"]), str(i["doctor_id"])
        if fid in users and did in users:
            jid = str(i["job_id"]) if i["job_id"] is not None and str(i["job_id"]) in jobs else None
            store.add("invitations", _pick("invitations", i, facility_id=fid, doctor_id=did, job_id=jid),
                      doc_id=str(i["id"]))
            done("invitations")
    # Jobs and applications came across, so don't add demo ones on top.
    if jobs:
        store.create("_meta", "demo-jobs", {"at": store.now()}, defaults=False)
        store.create("_meta", "demo-applications", {"at": store.now()}, defaults=False)
    for e in _rows(conn, "enquiries"):
        store.add("enquiries", _pick("enquiries", e), doc_id=str(e["id"]))
        done("enquiries")
    conn.close()
    return "Imported: " + (", ".join(f"{n} {k}" for k, n in report.items()) or "nothing")
