import csv
import io

from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, url_for

from .. import mail, refdata
from ..db import execute, query
from ..security import login_required
from . import page_args
from .facility import DOCTOR_SELECT

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required("admin")
def dashboard():
    counts = query(
        "SELECT (SELECT COUNT(*) FROM doctors) AS doctors,"
        " (SELECT COUNT(*) FROM doctors WHERE verified = 0) AS doctors_unverified,"
        " (SELECT COUNT(*) FROM facilities) AS facilities,"
        " (SELECT COUNT(*) FROM facilities WHERE verified = 0) AS facilities_pending,"
        " (SELECT COUNT(*) FROM jobs WHERE status = 'open') AS open_jobs,"
        " (SELECT COUNT(*) FROM applications) AS applications,"
        " (SELECT COUNT(*) FROM applications WHERE status = 'placed') AS placed,"
        " (SELECT COUNT(*) FROM applications WHERE created_at >= datetime('now', '-7 days')) AS apps_week",
        one=True)
    pending = query("SELECT f.*, u.email, u.created_at, ci.name AS city FROM facilities f JOIN users u ON u.id = f.user_id"
                    " LEFT JOIN cities ci ON ci.id = f.city_id WHERE f.verified = 0 ORDER BY u.created_at")
    recent_doctors = query(DOCTOR_SELECT.replace("SELECT d.*,", "SELECT d.*, u.created_at,", 1)
                           + " ORDER BY u.created_at DESC LIMIT 6")
    recent_apps = query(
        "SELECT a.*, j.title, f.name AS facility, d.first_name, d.last_name FROM applications a"
        " JOIN jobs j ON j.id = a.job_id JOIN facilities f ON f.user_id = j.facility_id"
        " JOIN doctors d ON d.user_id = a.doctor_id ORDER BY a.created_at DESC LIMIT 8")
    enquiries = query("SELECT * FROM enquiries ORDER BY created_at DESC LIMIT 5")
    return render_template("admin/dashboard.html", counts=counts, pending=pending, recent_doctors=recent_doctors,
                           recent_apps=recent_apps, enquiries=enquiries)


# ------------------------------------------------------------------ doctors

@bp.route("/doctors")
@login_required("admin")
def doctors():
    f = {k: request.args.get(k, "").strip() for k in ("q", "specialty", "verified")}
    where, args = [], []
    if f["q"]:
        where.append("(d.first_name || ' ' || d.last_name LIKE ? OR u.email LIKE ?)")
        args += [f"%{f['q']}%"] * 2
    if f["specialty"].isdigit():
        where.append("d.specialty_id = ?")
        args.append(int(f["specialty"]))
    if f["verified"] in ("0", "1"):
        where.append("d.verified = ?")
        args.append(int(f["verified"]))
    w = (" WHERE " + " AND ".join(where)) if where else ""
    if request.args.get("export") == "csv":
        return _doctors_csv(query(DOCTOR_SELECT + w + " ORDER BY d.last_name", args))
    page, per, offset = page_args(30)
    total = query("SELECT COUNT(*) AS n FROM doctors d JOIN users u ON u.id = d.user_id" + w, args, one=True)["n"]
    rows = query(DOCTOR_SELECT.replace("SELECT d.*,", "SELECT d.*, u.created_at,", 1) + w
                 + " ORDER BY u.created_at DESC LIMIT ? OFFSET ?", args + [per, offset])
    specialties = query("SELECT id, name FROM specialties ORDER BY name")
    return render_template("admin/doctors.html", rows=rows, f=f, total=total, page=page, per=per,
                           specialties=specialties)


def _doctors_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Email", "Phone", "Specialty", "Grade", "Years", "Nationality", "Lives in",
                "Qatar licence", "Available from", "Available to", "Verified", "Has CV"])
    for d in rows:
        w.writerow([f"{d['title']} {d['first_name']} {d['last_name']}", d["email"], d["phone"], d["specialty"],
                    refdata.label(refdata.GRADES, d["grade"]), d["years_experience"], d["nationality"],
                    d["current_country"], refdata.label(refdata.QATAR_LICENSE_STATUS, d["qatar_license_status"]),
                    d["available_from"], d["available_to"], "yes" if d["verified"] else "no",
                    "yes" if d["cv_count"] else "no"])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=locumdoc-doctors.csv"})


@bp.route("/doctors/<int:doctor_id>", methods=["GET", "POST"])
@login_required("admin")
def doctor(doctor_id):
    d = query(DOCTOR_SELECT.replace("SELECT d.*,", "SELECT d.*, u.created_at, u.last_login_at, u.is_active,", 1)
              + " WHERE d.user_id = ?", (doctor_id,), one=True)
    if not d:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "verify":
            execute("UPDATE doctors SET verified = 1 - verified WHERE user_id = ?", (doctor_id,))
            if not d["verified"]:
                mail.send(d["email"], "Your LocumDoc profile is verified", "doctor_verified", doctor=d)
            flash("Verification updated.", "success")
        elif action == "notes":
            execute("UPDATE doctors SET admin_notes = ? WHERE user_id = ?",
                    ((request.form.get("admin_notes") or "")[:5000], doctor_id))
            flash("Notes saved.", "success")
        elif action == "suspend":
            execute("UPDATE users SET is_active = 1 - is_active WHERE id = ?", (doctor_id,))
            flash("Account access updated.", "success")
        return redirect(url_for(".doctor", doctor_id=doctor_id))
    docs = query("SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC", (doctor_id,))
    apps = query("SELECT a.*, j.title, f.name AS facility FROM applications a JOIN jobs j ON j.id = a.job_id"
                 " JOIN facilities f ON f.user_id = j.facility_id WHERE a.doctor_id = ? ORDER BY a.created_at DESC",
                 (doctor_id,))
    return render_template("admin/doctor.html", d=d, docs=docs, apps=apps)


# --------------------------------------------------------------- facilities

@bp.route("/facilities")
@login_required("admin")
def facilities():
    status = request.args.get("verified", "")
    where, args = "", []
    if status in ("0", "1"):
        where, args = " WHERE f.verified = ?", [int(status)]
    rows = query(
        "SELECT f.*, u.email, u.created_at, ci.name AS city,"
        " (SELECT COUNT(*) FROM jobs j WHERE j.facility_id = f.user_id) AS job_count"
        " FROM facilities f JOIN users u ON u.id = f.user_id LEFT JOIN cities ci ON ci.id = f.city_id"
        + where + " ORDER BY f.verified, u.created_at DESC", args)
    return render_template("admin/facilities.html", rows=rows, status=status)


@bp.route("/facilities/<int:fac_id>", methods=["GET", "POST"])
@login_required("admin")
def facility(fac_id):
    fac = query("SELECT f.*, u.email, u.created_at, u.last_login_at, u.is_active, ci.name AS city, co.name AS country"
                " FROM facilities f JOIN users u ON u.id = f.user_id LEFT JOIN cities ci ON ci.id = f.city_id"
                " LEFT JOIN countries co ON co.id = f.country_id WHERE f.user_id = ?", (fac_id,), one=True)
    if not fac:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "verify":
            execute("UPDATE facilities SET verified = 1 - verified WHERE user_id = ?", (fac_id,))
            if not fac["verified"]:
                mail.send(fac["email"], "Your facility is verified on LocumDoc", "facility_verified", fac=fac)
                flash(f"{fac['name']} verified. Its open jobs are now live.", "success")
            else:
                flash(f"{fac['name']} unverified. Its jobs are hidden.", "info")
        elif action == "notes":
            execute("UPDATE facilities SET admin_notes = ? WHERE user_id = ?",
                    ((request.form.get("admin_notes") or "")[:5000], fac_id))
            flash("Notes saved.", "success")
        elif action == "suspend":
            execute("UPDATE users SET is_active = 1 - is_active WHERE id = ?", (fac_id,))
            flash("Account access updated.", "success")
        return redirect(url_for(".facility", fac_id=fac_id))
    jobs = query("SELECT j.*, s.name AS specialty, (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id)"
                 " AS applicants FROM jobs j JOIN specialties s ON s.id = j.specialty_id WHERE j.facility_id = ?"
                 " ORDER BY j.created_at DESC", (fac_id,))
    return render_template("admin/facility.html", fac=fac, jobs=jobs)


# -------------------------------------------------------------- jobs & apps

@bp.route("/jobs")
@login_required("admin")
def jobs():
    status = request.args.get("status", "open")
    args = []
    where = ""
    if status in dict(refdata.JOB_STATUSES):
        where, args = " WHERE j.status = ?", [status]
    rows = query(
        "SELECT j.*, s.name AS specialty, f.name AS facility, f.verified, ci.name AS city,"
        " (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id) AS applicants"
        " FROM jobs j JOIN specialties s ON s.id = j.specialty_id JOIN facilities f ON f.user_id = j.facility_id"
        " LEFT JOIN cities ci ON ci.id = j.city_id" + where + " ORDER BY j.created_at DESC", args)
    return render_template("admin/jobs.html", rows=rows, status=status)


@bp.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required("admin")
def job_status(job_id):
    status = request.form.get("status")
    if status not in dict(refdata.JOB_STATUSES):
        abort(400)
    execute("UPDATE jobs SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, job_id))
    flash("Job status updated.", "success")
    return redirect(request.form.get("back") or url_for(".jobs"))


@bp.route("/applications")
@login_required("admin")
def applications():
    status = request.args.get("status", "")
    where, args = "", []
    if status in dict(refdata.APPLICATION_STATUSES):
        where, args = " WHERE a.status = ?", [status]
    page, per, offset = page_args(40)
    rows = query(
        "SELECT a.*, j.title, f.name AS facility, d.first_name, d.last_name, s.name AS specialty FROM applications a"
        " JOIN jobs j ON j.id = a.job_id JOIN facilities f ON f.user_id = j.facility_id"
        " JOIN doctors d ON d.user_id = a.doctor_id LEFT JOIN specialties s ON s.id = j.specialty_id"
        + where + " ORDER BY a.created_at DESC LIMIT ? OFFSET ?", args + [per, offset])
    total = query("SELECT COUNT(*) AS n FROM applications a" + where, args, one=True)["n"]
    return render_template("admin/applications.html", rows=rows, status=status, page=page, per=per, total=total)


# ------------------------------------------------------- countries & inbox

@bp.route("/countries", methods=["GET", "POST"])
@login_required("admin")
def countries():
    if request.method == "POST":
        cid = request.form.get("country_id", type=int)
        if request.form.get("action") == "toggle":
            execute("UPDATE countries SET active = 1 - active WHERE id = ?", (cid,))
            flash("Country availability updated.", "success")
        elif request.form.get("action") == "add_city":
            name = (request.form.get("city") or "").strip()[:80]
            if name:
                execute("INSERT OR IGNORE INTO cities (country_id, name) VALUES (?, ?)", (cid, name))
                flash(f"{name} added.", "success")
        return redirect(url_for(".countries"))
    rows = query("SELECT co.*, (SELECT GROUP_CONCAT(name, ', ') FROM cities WHERE country_id = co.id) AS city_list,"
                 " (SELECT COUNT(*) FROM jobs WHERE country_id = co.id AND status = 'open') AS open_jobs"
                 " FROM countries co ORDER BY sort_order")
    return render_template("admin/countries.html", rows=rows)


@bp.route("/enquiries")
@login_required("admin")
def enquiries():
    rows = query("SELECT * FROM enquiries ORDER BY created_at DESC LIMIT 200")
    return render_template("admin/enquiries.html", rows=rows)
