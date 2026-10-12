"""Records and the lookups views need, on top of store.py (Firestore in production).

Firestore has no SQL joins, so the helpers here fetch the related records (the job's
facility, the doctor's specialty...) and merge the fields a page shows into one dict.
Lookups are cached per request by store.py, so this stays cheap.
"""
import os
import re
from datetime import date, timedelta

import click
from werkzeug.security import generate_password_hash

from . import refdata, storage, store


class EmailTaken(ValueError):
    pass


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def city_id_for(country_code, name):
    return f"{country_code.lower()}-{slugify(name)}"


# ------------------------------------------------------------ reference data

def seed_reference():
    """Add countries, cities and specialties that are missing. Never overwrites admin changes."""
    have = {c["id"] for c in store.find("countries")}
    for code, name, slug, cur, body, active, sort in refdata.COUNTRIES:
        if code not in have:
            store.create("countries", code, {"code": code, "name": name, "slug": slug, "currency": cur,
                                             "licensing_body": body, "active": 1 if active else 0,
                                             "sort_order": sort})
    have = {c["id"] for c in store.find("cities")}
    for code, names in refdata.CITIES.items():
        for name in names:
            cid = city_id_for(code, name)
            if cid not in have:
                store.create("cities", cid, {"country_id": code, "name": name})
    have = {s["id"] for s in store.find("specialties")}
    for name in refdata.SPECIALTIES:
        slug = slugify(name)
        if slug not in have:
            store.create("specialties", slug, {"name": name, "slug": slug})


def specialties():
    return sorted(store.find("specialties"), key=lambda s: s["name"])


def specialty_name(sid):
    s = store.get("specialties", sid)
    return s["name"] if s else None


def countries():
    return sorted(store.find("countries"), key=lambda c: (c["sort_order"], c["name"]))


def cities(active_only=False, include=None):
    """Cities with their country's name and currency, ordered like the old SQL (country, then name)."""
    by_code = {c["id"]: c for c in store.find("countries")}
    out = []
    for ci in store.find("cities"):
        co = by_code.get(ci["country_id"])
        if not co:
            continue
        if active_only and not co["active"] and ci["id"] != include:
            continue
        out.append(dict(ci, country=co["name"], currency=co["currency"], _sort=co["sort_order"]))
    return sorted(out, key=lambda c: (c["_sort"], c["name"]))


# --------------------------------------------------------------------- users

def user_by_email(email):
    return store.first("users", email=(email or "").strip().lower())


def create_user(email, password, role, lang="en"):
    """Create a login. Raises EmailTaken if the address is already registered (checked atomically)."""
    email = email.strip().lower()
    uid = store._backend().new_id("users")
    if not store.create("emails", store.email_key(email), {"user_id": uid}, defaults=False):
        raise EmailTaken(email)
    store.add("users", {"email": email, "password_hash": generate_password_hash(password), "role": role,
                        "lang": lang}, doc_id=uid)
    return uid


def delete_user(uid):
    """Remove an account and everything that belongs to it (profile, files, jobs, applications)."""
    user = store.get("users", uid)
    if not user:
        return
    for d in store.find("documents", user_id=uid):
        storage.delete(d["storage_name"])
        store.delete("documents", d["id"])
    store.delete_where("applications", doctor_id=uid)
    store.delete_where("invitations", doctor_id=uid)
    store.delete_where("invitations", facility_id=uid)
    for j in store.find("jobs", facility_id=uid):
        store.delete_where("applications", job_id=j["id"])
        for inv in store.find("invitations", job_id=j["id"]):
            store.update("invitations", inv["id"], job_id=None)
        store.delete("jobs", j["id"])
    store.delete("doctors", uid)
    store.delete("facilities", uid)
    store.delete("emails", store.email_key(user["email"]))
    store.delete("users", uid)


# ----------------------------------------------------- joined views of records

def doctor_full(d):
    """A doctor profile plus account details, specialty name and whether a CV is on file."""
    if d is None:
        return None
    u = store.get("users", d["id"]) or {}
    docs = store.find("documents", user_id=d["id"])
    return dict(d, email=u.get("email", ""), lang=u.get("lang", "en"), created_at=u.get("created_at"),
                last_login_at=u.get("last_login_at"), is_active=u.get("is_active", 0),
                specialty=specialty_name(d["specialty_id"]),
                cv_count=sum(1 for x in docs if x["kind"] == "cv"))


def get_doctor(uid):
    return doctor_full(store.get("doctors", uid))


def facility_full(f):
    if f is None:
        return None
    u = store.get("users", f["id"]) or {}
    ci = store.get("cities", f["city_id"])
    co = store.get("countries", f["country_id"])
    return dict(f, email=u.get("email", ""), lang=u.get("lang", "en"), created_at=u.get("created_at"),
                last_login_at=u.get("last_login_at"), is_active=u.get("is_active", 0),
                city=ci["name"] if ci else None, country=co["name"] if co else None,
                currency=co["currency"] if co else None)


def get_facility(uid):
    return facility_full(store.get("facilities", uid))


def job_full(j):
    """A job plus the names the listings show: specialty, city, country, facility."""
    if j is None:
        return None
    co = store.get("countries", j["country_id"]) or {}
    ci = store.get("cities", j["city_id"])
    f = store.get("facilities", j["facility_id"]) or {}
    return dict(j, specialty=specialty_name(j["specialty_id"]), city=ci["name"] if ci else None,
                country=co.get("name"), country_slug=co.get("slug"), country_active=co.get("active", 0),
                facility=f.get("name"), facility_type=f.get("facility_type"), sector=f.get("sector"),
                facility_verified=f.get("verified", 0))


def get_job(job_id):
    return job_full(store.get("jobs", job_id))


def is_public(job):
    return (job["status"] == "open" and job["facility_verified"] and job["country_active"]
            and job["end_date"] >= date.today().isoformat())


def public_jobs(match=None, limit=None, offset=0):
    """Open jobs at verified facilities in open countries, soonest start first."""
    rows = [job_full(j) for j in store.find("jobs", status="open")]
    rows = [r for r in rows if is_public(r) and (match is None or match(r))]
    rows.sort(key=lambda r: (r["start_date"], r["created_at"]))
    return rows[offset:offset + limit] if limit else rows[offset:]


def application_full(a, specialty_of="doctor"):
    """An application with its job, facility, city and doctor fields merged in."""
    j = store.get("jobs", a["job_id"]) or {}
    d = store.get("doctors", a["doctor_id"]) or {}
    f = store.get("facilities", j.get("facility_id")) or {}
    ci = store.get("cities", j.get("city_id"))
    spec = j.get("specialty_id") if specialty_of == "job" else d.get("specialty_id")
    return dict(a, title=j.get("title", ""), start_date=j.get("start_date"), end_date=j.get("end_date"),
                rate_amount=j.get("rate_amount"), rate_currency=j.get("rate_currency"),
                rate_period=j.get("rate_period"), job_status=j.get("status"), facility_id=j.get("facility_id"),
                facility=f.get("name"), city=ci["name"] if ci else None,
                dtitle=d.get("title"), first_name=d.get("first_name", ""), last_name=d.get("last_name", ""),
                grade=d.get("grade"), academic_rank=d.get("academic_rank"),
                years_experience=d.get("years_experience"), qatar_license_status=d.get("qatar_license_status"),
                current_country=d.get("current_country"), available_from=d.get("available_from"),
                specialty=specialty_name(spec))


def invitation_full(i):
    f = store.get("facilities", i["facility_id"]) or {}
    j = store.get("jobs", i["job_id"])
    title = j["title"] if j else None
    return dict(i, facility=f.get("name"), job_title=title, title=title)


def newest_first(rows, key="created_at"):
    return sorted(rows, key=lambda r: r.get(key) or "", reverse=True)


def documents_for(uid, cv_first=True):
    docs = newest_first(store.find("documents", user_id=uid))
    if cv_first:
        docs.sort(key=lambda d: d["kind"] != "cv")
    return docs


# ---------------------------------------------------------------- demo content

DEMO_FACILITIES = [
    # name, type, sector, city, contact
    ("Corniche Medical Centre (demo)", "polyclinic", "private", "Doha", "Reem Al-Sayed"),
    ("West Bay Specialist Hospital (demo)", "hospital", "private", "Doha", "Daniel Hughes"),
    ("Al Wakrah Family Clinic (demo)", "primary_care", "private", "Al Wakrah", "Noura Khalid"),
]

DEMO_JOBS = [
    # facility idx, title, specialty, grade, city, start in days, weeks, rate, period, perks(acc, fl, tr, lic)
    (1, "Locum consultant anaesthetist", "Anaesthesia", "consultant", "Doha", 30, 12, 72000, "month", (1, 1, 1, 1)),
    (1, "Emergency medicine specialist, night rota", "Emergency Medicine", "specialist", "Doha", 21, 8, 2600, "day", (1, 1, 0, 1)),
    (0, "Paediatrician for winter cover", "Paediatrics", "specialist", "Doha", 45, 16, 48000, "month", (1, 0, 1, 1)),
    (2, "Family medicine GP, weekday clinics", "Family Medicine", "gp", "Al Wakrah", 14, 26, 38000, "month", (0, 0, 1, 1)),
    (1, "Consultant radiologist (MSK reporting)", "Radiology", "consultant", "Doha", 60, 12, 19500, "week", (1, 1, 1, 1)),
    (0, "Obstetrics & gynaecology specialist", "Obstetrics & Gynaecology", "specialist", "Doha", 35, 12, 55000, "month", (1, 1, 1, 0)),
    (1, "ICU consultant, 3-month cover", "Critical Care / ICU", "consultant", "Doha", 50, 13, 78000, "month", (1, 1, 1, 1)),
    (2, "Dermatology specialist, two days a week", "Dermatology", "specialist", "Al Wakrah", 28, 20, 3100, "day", (0, 0, 0, 1)),
]

DEMO_DOCTORS = [
    ("Sarah", "Mitchell", "Anaesthesia", "consultant", 14, "United Kingdom", "United Kingdom",
     "MBBS, FRCA, CCT Anaesthesia", "GMC full registration with licence to practise", "eligible", "exempt"),
    ("Omar", "Haddad", "Emergency Medicine", "specialist", 9, "Jordan", "Jordan",
     "MD, Arab Board Emergency Medicine", "Jordan Medical Council", "evaluating", "passed"),
    ("Priya", "Raman", "Paediatrics", "specialist", 11, "Ireland", "India",
     "MB BCh, MRCPCH", "IMC specialist registration", "none", "exempt"),
    ("Youssef", "Mansour", "Radiology", "consultant", 17, "Egypt", "Egypt",
     "MBBCh, MD Radiology, FRCR", "Egyptian Medical Syndicate", "licensed", "exempt"),
]

DEMO_SCHOOLS = [("University of Bristol", 2008), ("University of Jordan", 2013),
                ("Royal College of Surgeons in Ireland", 2011), ("Cairo University (Kasr Al Ainy)", 2005)]
DEMO_ACADEMIC = {3: "eg_assistant_professor"}


def seed_demo():
    """Demo facilities, jobs, doctors and applications. Safe to run on every start."""
    fac_ids = []
    for i, (name, ftype, sector, cname, contact) in enumerate(DEMO_FACILITIES):
        email = f"facility{i + 1}@demo.locumdoc.me"
        u = user_by_email(email)
        if u:
            fac_ids.append(u["id"])
            continue
        try:
            uid = create_user(email, "demo-password", "facility")
        except EmailTaken:  # another worker is seeding at the same moment
            return
        store.add("facilities", {"user_id": uid, "name": name, "facility_type": ftype, "sector": sector,
                                 "country_id": "QA", "city_id": city_id_for("QA", cname), "contact_name": contact,
                                 "contact_role": "Medical staffing lead", "phone": "+974 4000 0000",
                                 "about": "Demo facility used to preview the platform.", "verified": 1}, doc_id=uid)
        fac_ids.append(uid)
    if store.create("_meta", "demo-jobs", {"at": store.now()}, defaults=False):
        today = date.today()
        for fidx, title, sname, grade, cname, start, weeks, rate, period, perks in DEMO_JOBS:
            s = today + timedelta(days=start)
            e = s + timedelta(weeks=weeks)
            acc, fl, tr, lic = perks
            store.add("jobs", {
                "facility_id": fac_ids[fidx], "title": title, "specialty_id": slugify(sname), "grade": grade,
                "country_id": "QA", "city_id": city_id_for("QA", cname), "start_date": s.isoformat(),
                "end_date": e.isoformat(), "rate_amount": rate, "rate_currency": "QAR", "rate_period": period,
                "accommodation": acc, "flights": fl, "transport": tr, "licensing_support": lic,
                "description": "Cover for a planned absence in a busy department. Full induction, rota shared in "
                               "advance, and a named clinical lead for the duration of the placement.",
                "requirements": "Specialty qualification recognised by DHP (category 1 or 2 preferred). "
                                "At least 3 years post-specialty experience. Current certificate of good standing."})
    for i, (fn, ln, sname, grade, yrs, country, nat, quals, lic, qstat, exam) in enumerate(DEMO_DOCTORS):
        email = f"doctor{i + 1}@demo.locumdoc.me"
        if user_by_email(email):
            continue
        try:
            uid = create_user(email, "demo-password", "doctor")
        except EmailTaken:
            continue
        avail = date.today() + timedelta(days=20 + i * 10)
        school, year = DEMO_SCHOOLS[i]
        store.add("doctors", {
            "user_id": uid, "first_name": fn, "last_name": ln, "phone": "+44 7700 900000", "nationality": nat,
            "current_country": country, "specialty_id": slugify(sname), "grade": grade,
            "academic_rank": DEMO_ACADEMIC.get(i, ""), "years_experience": yrs, "qualifications": quals,
            "medical_school": school, "graduation_year": year, "primary_license": lic,
            "qatar_license_status": qstat, "exam_status": exam, "has_psv": 1 if qstat != "none" else 0,
            "good_standing": 1, "languages": "English, Arabic" if nat in ("Jordan", "Egypt") else "English",
            "available_from": avail.isoformat(), "available_to": (avail + timedelta(weeks=16)).isoformat(),
            "min_weeks": 8, "bio": "Demo profile. Experienced locum available for blocks of 2 to 4 months.",
            "verified": 1 if i % 2 == 0 else 0}, doc_id=uid)
        pdf = _demo_pdf(f"Dr {fn} {ln}", sname, quals)
        name = storage.write_bytes(pdf)
        store.add("documents", {"user_id": uid, "kind": "cv", "original_name": f"CV {fn} {ln}.pdf",
                                "storage_name": name, "mime_type": "application/pdf", "size_bytes": len(pdf)})
    if store.create("_meta", "demo-applications", {"at": store.now()}, defaults=False):
        for email, specialty, status in (("doctor1@demo.locumdoc.me", "Anaesthesia", "shortlisted"),
                                         ("doctor4@demo.locumdoc.me", "Radiology", "submitted"),
                                         ("doctor2@demo.locumdoc.me", "Emergency Medicine", "interview")):
            u = user_by_email(email)
            jobs = store.find("jobs", specialty_id=slugify(specialty))
            if u and jobs:
                jid = jobs[0]["id"]
                store.create("applications", f"{jid}_{u['id']}", {
                    "job_id": jid, "doctor_id": u["id"], "status": status,
                    "cover_note": "Available for the full placement. PSV report ready."})


def _demo_pdf(*lines):
    """A minimal one-page PDF, so demo profiles have a CV to open."""
    text = "BT /F1 18 Tf 72 740 Td (Curriculum vitae - demo) Tj /F1 12 Tf"
    for ln in lines:
        safe = ln.replace("\\", "").replace("(", "").replace(")", "")
        text += f" 0 -24 Td ({safe}) Tj"
    text += " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


# ---------------------------------------------------------------- start-up

def register_cli(app):
    @app.cli.command("init-db")
    def init_db_cmd():
        """Load reference data (countries, cities, specialties)."""
        seed_reference()
        click.echo("Database ready.")

    @app.cli.command("seed-demo")
    def seed_demo_cmd():
        """Add demo facilities, jobs and doctors (password: demo-password)."""
        seed_demo()
        click.echo("Demo data added.")

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.password_option()
    def create_admin_cmd(email, password):
        """Create an administrator account."""
        try:
            create_user(email, password, "admin")
        except EmailTaken:
            raise click.ClickException("A user with that email already exists.")
        click.echo(f"Admin {email} created.")

    @app.cli.command("import-sqlite")
    @click.argument("sqlite_path")
    @click.option("--uploads", default=None, help="Folder holding the uploaded files (default: next to the database).")
    def import_sqlite_cmd(sqlite_path, uploads):
        """Copy records and uploaded PDFs from the old SQLite database into the current store."""
        from .import_sqlite import run
        click.echo(run(sqlite_path, uploads))


def _import_legacy_sqlite(app):
    """On a computer that ran the old SQLite version, bring its accounts across on first start."""
    path = app.config.get("LEGACY_SQLITE_PATH")
    if (isinstance(store._backend(), store.LocalBackend) and path and os.path.exists(path)
            and not store.find("users")):
        from .import_sqlite import run
        app.logger.warning("Moved data from %s: %s", path, run(path))


def ensure_db(app):
    """Load reference data and the admin account on start-up, so a fresh project works without manual steps."""
    with app.app_context():
        seed_reference()
        _import_legacy_sqlite(app)
        admin_email = app.config.get("ADMIN_EMAIL")
        admin_pw = app.config.get("ADMIN_PASSWORD")
        if admin_email and admin_pw and not user_by_email(admin_email):
            try:
                create_user(admin_email, admin_pw, "admin")
            except EmailTaken:
                pass  # another worker created it first
        if app.config.get("SEED_DEMO"):
            seed_demo()
