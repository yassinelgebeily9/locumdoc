import os
import re
import sqlite3
from datetime import date, timedelta

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash

from . import refdata


def get_db():
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        g.db = conn
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def init_schema():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))
    migrate()
    seed_reference()


def migrate():
    """Small in-place upgrades for databases created by earlier versions."""
    db = get_db()
    cols = {r[1] for r in db.execute("PRAGMA table_info(users)")}
    if "lang" not in cols:
        db.execute("ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'en'")
    db.commit()


def seed_reference():
    """Insert countries, cities and specialties if missing. Safe to run repeatedly."""
    db = get_db()
    for code, name, slug, cur, body, active, sort in refdata.COUNTRIES:
        db.execute(
            "INSERT OR IGNORE INTO countries (code, name, slug, currency, licensing_body, active, sort_order)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, name, slug, cur, body, 1 if active else 0, sort),
        )
    for code, cities in refdata.CITIES.items():
        cid = db.execute("SELECT id FROM countries WHERE code = ?", (code,)).fetchone()[0]
        for city in cities:
            db.execute("INSERT OR IGNORE INTO cities (country_id, name) VALUES (?, ?)", (cid, city))
    for name in refdata.SPECIALTIES:
        db.execute("INSERT OR IGNORE INTO specialties (name, slug) VALUES (?, ?)", (name, slugify(name)))
    db.commit()


def create_user(email, password, role, lang="en"):
    return execute(
        "INSERT INTO users (email, password_hash, role, lang) VALUES (?, ?, ?, ?)",
        (email.strip().lower(), generate_password_hash(password), role, lang),
    )


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
    ("Sarah", "Mitchell", "Anaesthesia", "consultant", 14, "United Kingdom", "British",
     "MBBS, FRCA, CCT Anaesthesia", "GMC full registration with licence to practise", "eligible", "exempt"),
    ("Omar", "Haddad", "Emergency Medicine", "specialist", 9, "Jordan", "Jordanian",
     "MD, Arab Board Emergency Medicine", "Jordan Medical Council", "evaluating", "passed"),
    ("Priya", "Raman", "Paediatrics", "specialist", 11, "Ireland", "Irish",
     "MB BCh, MRCPCH", "IMC specialist registration", "none", "exempt"),
    ("Youssef", "Mansour", "Radiology", "consultant", 17, "Egypt", "Egyptian",
     "MBBCh, MD Radiology, FRCR", "Egyptian Medical Syndicate", "licensed", "exempt"),
]


def seed_demo():
    db = get_db()
    qa = db.execute("SELECT id FROM countries WHERE code='QA'").fetchone()[0]
    city = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM cities WHERE country_id=?", (qa,))}
    spec = {r["name"]: r["id"] for r in db.execute("SELECT id, name FROM specialties")}
    fac_ids = []
    for i, (name, ftype, sector, cname, contact) in enumerate(DEMO_FACILITIES):
        email = f"facility{i + 1}@demo.locumdoc.me"
        row = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if row:
            fac_ids.append(row[0])
            continue
        uid = create_user(email, "demo-password", "facility")
        db.execute(
            "INSERT INTO facilities (user_id, name, facility_type, sector, country_id, city_id, contact_name,"
            " contact_role, phone, about, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (uid, name, ftype, sector, qa, city[cname], contact, "Medical staffing lead",
             "+974 4000 0000", "Demo facility used to preview the platform."),
        )
        fac_ids.append(uid)
    if db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
        today = date.today()
        for fidx, title, sname, grade, cname, start, weeks, rate, period, perks in DEMO_JOBS:
            s = today + timedelta(days=start)
            e = s + timedelta(weeks=weeks)
            db.execute(
                "INSERT INTO jobs (facility_id, title, specialty_id, grade, country_id, city_id, start_date, end_date,"
                " rate_amount, rate_currency, rate_period, accommodation, flights, transport, licensing_support,"
                " description, requirements) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'QAR', ?, ?, ?, ?, ?, ?, ?)",
                (fac_ids[fidx], title, spec[sname], grade, qa, city[cname], s.isoformat(), e.isoformat(),
                 rate, period, *perks,
                 "Cover for a planned absence in a busy department. Full induction, rota shared in advance, "
                 "and a named clinical lead for the duration of the placement.",
                 "Specialty qualification recognised by DHP (category 1 or 2 preferred). "
                 "At least 3 years post-specialty experience. Current certificate of good standing."),
            )
    for i, (fn, ln, sname, grade, yrs, country, nat, quals, lic, qstat, exam) in enumerate(DEMO_DOCTORS):
        email = f"doctor{i + 1}@demo.locumdoc.me"
        if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            continue
        uid = create_user(email, "demo-password", "doctor")
        avail = date.today() + timedelta(days=20 + i * 10)
        db.execute(
            "INSERT INTO doctors (user_id, first_name, last_name, phone, nationality, current_country, specialty_id,"
            " grade, years_experience, qualifications, primary_license, qatar_license_status, exam_status, has_psv,"
            " good_standing, languages, available_from, available_to, min_weeks, bio, verified)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)",
            (uid, fn, ln, "+44 7700 900000", nat, country, spec[sname], grade, yrs, quals, lic, qstat, exam,
             1 if qstat != "none" else 0, "English, Arabic" if nat in ("Jordanian", "Egyptian") else "English",
             avail.isoformat(), (avail + timedelta(weeks=16)).isoformat(), 8,
             "Demo profile. Experienced locum available for blocks of 2 to 4 months.", 1 if i % 2 == 0 else 0),
        )
        name = f"demo-cv-{uid}.pdf"
        with open(os.path.join(current_app.config["UPLOAD_DIR"], name), "wb") as fh:
            fh.write(_demo_pdf(f"Dr {fn} {ln}", sname, quals))
        db.execute("INSERT INTO documents (user_id, kind, original_name, storage_name, mime_type, size_bytes)"
                   " VALUES (?, 'cv', ?, ?, 'application/pdf', ?)",
                   (uid, f"CV {fn} {ln}.pdf", name, os.path.getsize(os.path.join(current_app.config["UPLOAD_DIR"], name))))
    db.commit()
    if db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0:
        for email, specialty, status in (("doctor1@demo.locumdoc.me", "Anaesthesia", "shortlisted"),
                                         ("doctor4@demo.locumdoc.me", "Radiology", "submitted"),
                                         ("doctor2@demo.locumdoc.me", "Emergency Medicine", "interview")):
            row = db.execute(
                "SELECT u.id AS uid, j.id AS jid FROM users u, jobs j WHERE u.email = ? AND j.specialty_id = ?"
                " LIMIT 1", (email, spec[specialty])).fetchone()
            if row:
                db.execute("INSERT OR IGNORE INTO applications (job_id, doctor_id, cover_note, status) VALUES (?, ?, ?, ?)",
                           (row["jid"], row["uid"], "Available for the full placement. PSV report ready.", status))
        db.commit()


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


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_cmd():
        """Create tables and load reference data."""
        init_schema()
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
        if query("SELECT 1 FROM users WHERE email = ?", (email.lower(),), one=True):
            raise click.ClickException("A user with that email already exists.")
        create_user(email, password, "admin")
        click.echo(f"Admin {email} created.")


def ensure_db(app):
    """Create the database on first boot so a fresh deploy works without manual steps."""
    path = app.config["DATABASE"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with app.app_context():
        init_schema()
        admin_email = app.config.get("ADMIN_EMAIL")
        admin_pw = app.config.get("ADMIN_PASSWORD")
        if admin_email and admin_pw and not query("SELECT 1 FROM users WHERE email=?", (admin_email.lower(),), one=True):
            try:
                create_user(admin_email, admin_pw, "admin")
            except sqlite3.IntegrityError:
                pass  # another worker created it first
        if app.config.get("SEED_DEMO"):
            seed_demo()
