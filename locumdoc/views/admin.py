import csv
import io

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for

from .. import db, mail, phones, refdata, store
from ..i18n import _
from ..db import get_doctor, get_facility
from ..security import login_required
from . import page_args

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@login_required("admin")
def dashboard():
    doctors = store.find("doctors")
    facilities = store.find("facilities")
    apps = store.find("applications")
    week = store.days_ago(7)
    counts = {
        "doctors": len(doctors), "doctors_unverified": sum(1 for d in doctors if not d["verified"]),
        "facilities": len(facilities), "facilities_pending": sum(1 for f in facilities if not f["verified"]),
        "open_jobs": store.count("jobs", status="open"), "applications": len(apps),
        "placed": sum(1 for a in apps if a["status"] == "placed"),
        "apps_week": sum(1 for a in apps if (a["created_at"] or "") >= week),
    }
    pending = sorted((get_facility(f["id"]) for f in facilities if not f["verified"]),
                     key=lambda f: f["created_at"] or "")
    recent_doctors = db.newest_first([get_doctor(d["id"]) for d in doctors])[:6]
    recent_apps = [db.application_full(a) for a in db.newest_first(apps)[:8]]
    enquiries = db.newest_first(store.find("enquiries"))[:5]
    return render_template("admin/dashboard.html", counts=counts, pending=pending, recent_doctors=recent_doctors,
                           recent_apps=recent_apps, enquiries=enquiries)


# ------------------------------------------------------------------ doctors

def _contains(text, q):
    return q.casefold() in (text or "").casefold()


@bp.route("/doctors")
@login_required("admin")
def doctors():
    f = {k: request.args.get(k, "").strip() for k in ("q", "specialty", "verified")}
    rows = [get_doctor(d["id"]) for d in store.find("doctors")]
    if f["q"]:
        rows = [d for d in rows if _contains(f"{d['first_name']} {d['last_name']}", f["q"]) or _contains(d["email"], f["q"])]
    if f["specialty"]:
        rows = [d for d in rows if d["specialty_id"] == f["specialty"]]
    if f["verified"] in ("0", "1"):
        rows = [d for d in rows if d["verified"] == int(f["verified"])]
    if request.args.get("export") == "csv":
        return _doctors_csv(sorted(rows, key=lambda d: d["last_name"]))
    page, per, offset = page_args(30)
    rows = db.newest_first(rows)
    return render_template("admin/doctors.html", rows=rows[offset:offset + per], f=f, total=len(rows), page=page,
                           per=per, specialties=db.specialties())


def _doctors_csv(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Email", "Phone", "Specialty", "Grade", "Academic title", "Years", "University", "Graduated", "Nationality", "Lives in",
                "Qatar licence", "Available from", "Available to", "Verified", "Has CV"])
    for d in rows:
        w.writerow([f"{d['title']} {d['first_name']} {d['last_name']}", d["email"], phones.display(d["phone"]), d["specialty"],
                    refdata.label(refdata.GRADES, d["grade"]), refdata.label(refdata.ACADEMIC_RANKS, d["academic_rank"], ""),
                    d["years_experience"], d["medical_school"], d["graduation_year"] or "", d["nationality"],
                    d["current_country"], refdata.label(refdata.QATAR_LICENSE_STATUS, d["qatar_license_status"]),
                    d["available_from"], d["available_to"], "yes" if d["verified"] else "no",
                    "yes" if d["cv_count"] else "no"])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=locumdoc-doctors.csv"})


@bp.route("/doctors/<doctor_id>", methods=["GET", "POST"])
@login_required("admin")
def doctor(doctor_id):
    d = get_doctor(doctor_id)
    if not d:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "verify":
            store.update("doctors", doctor_id, verified=1 - d["verified"])
            if not d["verified"]:
                mail.send(d["email"], "Your LocumDoc profile is verified", "doctor_verified", d["lang"], doctor=d)
            flash(_("Verification updated."), "success")
        elif action == "notes":
            store.update("doctors", doctor_id, admin_notes=(request.form.get("admin_notes") or "")[:5000])
            flash(_("Notes saved."), "success")
        elif action == "suspend":
            store.update("users", doctor_id, is_active=1 - d["is_active"])
            flash(_("Account access updated."), "success")
        return redirect(url_for(".doctor", doctor_id=doctor_id))
    docs = db.documents_for(doctor_id, cv_first=False)
    apps = [db.application_full(a) for a in db.newest_first(store.find("applications", doctor_id=doctor_id))]
    return render_template("admin/doctor.html", d=d, docs=docs, apps=apps)


# --------------------------------------------------------------- facilities

@bp.route("/facilities")
@login_required("admin")
def facilities():
    status = request.args.get("verified", "")
    rows = [dict(get_facility(f["id"]), job_count=store.count("jobs", facility_id=f["id"]))
            for f in store.find("facilities") if status not in ("0", "1") or f["verified"] == int(status)]
    rows = sorted(db.newest_first(rows), key=lambda f: f["verified"])
    return render_template("admin/facilities.html", rows=rows, status=status)


@bp.route("/facilities/<fac_id>", methods=["GET", "POST"])
@login_required("admin")
def facility(fac_id):
    fac = get_facility(fac_id)
    if not fac:
        abort(404)
    if request.method == "POST":
        action = request.form.get("action")
        if action == "verify":
            store.update("facilities", fac_id, verified=1 - fac["verified"])
            if not fac["verified"]:
                mail.send(fac["email"], "Your facility is verified on LocumDoc", "facility_verified", fac["lang"], fac=fac)
                flash(f"{fac['name']} verified. Its open jobs are now live.", "success")
            else:
                flash(f"{fac['name']} unverified. Its jobs are hidden.", "info")
        elif action == "notes":
            store.update("facilities", fac_id, admin_notes=(request.form.get("admin_notes") or "")[:5000])
            flash(_("Notes saved."), "success")
        elif action == "suspend":
            store.update("users", fac_id, is_active=1 - fac["is_active"])
            flash(_("Account access updated."), "success")
        return redirect(url_for(".facility", fac_id=fac_id))
    jobs = [dict(j, specialty=db.specialty_name(j["specialty_id"]),
                 applicants=store.count("applications", job_id=j["id"]))
            for j in db.newest_first(store.find("jobs", facility_id=fac_id))]
    return render_template("admin/facility.html", fac=fac, jobs=jobs)


# -------------------------------------------------------------- jobs & apps

@bp.route("/jobs")
@login_required("admin")
def jobs():
    status = request.args.get("status", "open")
    jobs = store.find("jobs", status=status) if status in dict(refdata.JOB_STATUSES) else store.find("jobs")
    rows = []
    for j in db.newest_first(jobs):
        full = db.job_full(j)
        rows.append(dict(full, verified=full["facility_verified"],
                         applicants=store.count("applications", job_id=j["id"])))
    return render_template("admin/jobs.html", rows=rows, status=status)


@bp.route("/jobs/<job_id>/status", methods=["POST"])
@login_required("admin")
def job_status(job_id):
    status = request.form.get("status")
    if status not in dict(refdata.JOB_STATUSES):
        abort(400)
    store.update("jobs", job_id, status=status, updated_at=store.now())
    flash(_("Job status updated."), "success")
    return redirect(request.form.get("back") or url_for(".jobs"))


@bp.route("/applications")
@login_required("admin")
def applications():
    status = request.args.get("status", "")
    apps = (store.find("applications", status=status) if status in dict(refdata.APPLICATION_STATUSES)
            else store.find("applications"))
    page, per, offset = page_args(40)
    rows = [db.application_full(a, specialty_of="job") for a in db.newest_first(apps)[offset:offset + per]]
    total = len(apps)
    return render_template("admin/applications.html", rows=rows, status=status, page=page, per=per, total=total)


# ------------------------------------------------------- countries & inbox

@bp.route("/countries", methods=["GET", "POST"])
@login_required("admin")
def countries():
    if request.method == "POST":
        co = store.get("countries", request.form.get("country_id"))
        if not co:
            abort(404)
        if request.form.get("action") == "toggle":
            store.update("countries", co["id"], active=1 - co["active"])
            flash(_("Country availability updated."), "success")
        elif request.form.get("action") == "add_city":
            name = (request.form.get("city") or "").strip()[:80]
            if name and db.slugify(name):
                store.create("cities", db.city_id_for(co["id"], name), {"country_id": co["id"], "name": name})
                flash(f"{name} added.", "success")
        return redirect(url_for(".countries"))
    open_jobs = store.find("jobs", status="open")
    rows = [dict(co, city_list=", ".join(sorted(c["name"] for c in store.find("cities", country_id=co["id"]))),
                 open_jobs=sum(1 for j in open_jobs if j["country_id"] == co["id"]))
            for co in db.countries()]
    return render_template("admin/countries.html", rows=rows)


@bp.route("/enquiries")
@login_required("admin")
def enquiries():
    rows = db.newest_first(store.find("enquiries"))[:200]
    return render_template("admin/enquiries.html", rows=rows)
