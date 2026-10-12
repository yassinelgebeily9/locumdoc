from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import mail, refdata
from ..i18n import _
from ..db import execute, query
from ..security import login_required
from . import Form, page_args

bp = Blueprint("facility", __name__, url_prefix="/facility")

DOCTOR_SELECT = """
    SELECT d.*, u.email, s.name AS specialty,
           (SELECT COUNT(*) FROM documents x WHERE x.user_id = d.user_id AND x.kind = 'cv') AS cv_count
    FROM doctors d JOIN users u ON u.id = d.user_id LEFT JOIN specialties s ON s.id = d.specialty_id
"""


def get_facility(uid):
    return query(
        "SELECT f.*, u.email, ci.name AS city, co.name AS country, co.currency FROM facilities f"
        " JOIN users u ON u.id = f.user_id LEFT JOIN cities ci ON ci.id = f.city_id"
        " LEFT JOIN countries co ON co.id = f.country_id WHERE f.user_id = ?", (uid,), one=True)


def own_job(job_id):
    job = query("SELECT j.*, s.name AS specialty, ci.name AS city FROM jobs j JOIN specialties s ON s.id = j.specialty_id"
                " LEFT JOIN cities ci ON ci.id = j.city_id WHERE j.id = ? AND j.facility_id = ?",
                (job_id, g.user["id"]), one=True)
    if not job:
        abort(404)
    return job


def can_view_doctor(fac, doctor_id):
    if query("SELECT 1 FROM applications a JOIN jobs j ON j.id = a.job_id WHERE a.doctor_id = ? AND j.facility_id = ?"
             " AND a.status != 'withdrawn'", (doctor_id, fac["user_id"]), one=True):
        return True
    d = query("SELECT visible_to_facilities FROM doctors WHERE user_id = ?", (doctor_id,), one=True)
    return bool(fac["verified"] and d and d["visible_to_facilities"])


@bp.route("/")
@login_required("facility")
def dashboard():
    fac = get_facility(g.user["id"])
    jobs = query(
        "SELECT j.*, s.name AS specialty,"
        " (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id AND a.status != 'withdrawn') AS applicants,"
        " (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.id AND a.status = 'submitted') AS new_count"
        " FROM jobs j JOIN specialties s ON s.id = j.specialty_id WHERE j.facility_id = ?"
        " ORDER BY j.status = 'open' DESC, j.start_date", (g.user["id"],))
    recent = query(
        "SELECT a.*, j.title, d.first_name, d.last_name, d.grade, s.name AS specialty FROM applications a"
        " JOIN jobs j ON j.id = a.job_id JOIN doctors d ON d.user_id = a.doctor_id"
        " LEFT JOIN specialties s ON s.id = d.specialty_id WHERE j.facility_id = ? AND a.status != 'withdrawn'"
        " ORDER BY a.created_at DESC LIMIT 8", (g.user["id"],))
    return render_template("facility/dashboard.html", fac=fac, jobs=jobs, recent=recent)


@bp.route("/profile", methods=["GET", "POST"])
@login_required("facility")
def profile():
    fac = get_facility(g.user["id"])
    cities = query("SELECT ci.id, ci.name, co.name AS country FROM cities ci JOIN countries co ON co.id = ci.country_id"
                   " WHERE co.active = 1 OR ci.id = ? ORDER BY co.sort_order, ci.name", (fac["city_id"] or 0,))
    form = Form()
    if request.method == "POST":
        form.text("name", required=True, max_len=160, label=_("the facility name"))
        form.choice("facility_type", refdata.FACILITY_TYPES)
        form.choice("sector", refdata.SECTORS)
        form.choice("city_id", [(c["id"], c["name"]) for c in cities], label=_("a city"))
        form.text("website", max_len=200)
        form.text("contact_name", required=True, max_len=120, label=_("a contact name"))
        form.text("contact_role", max_len=120)
        form.text("phone", required=True, max_len=40, label=_("a phone number"))
        form.text("about", max_len=2000)
        if form.ok:
            c = form.clean
            city = query("SELECT * FROM cities WHERE id = ?", (int(c["city_id"]),), one=True)
            execute("UPDATE facilities SET name=?, facility_type=?, sector=?, country_id=?, city_id=?, website=?,"
                    " contact_name=?, contact_role=?, phone=?, about=?, updated_at=datetime('now') WHERE user_id=?",
                    (c["name"], c["facility_type"], c["sector"], city["country_id"], city["id"], c["website"],
                     c["contact_name"], c["contact_role"], c["phone"], c["about"], g.user["id"]))
            flash(_("Facility profile saved."), "success")
            return redirect(url_for(".dashboard"))
    v = dict(fac)
    if request.method == "POST":
        v.update(form.clean)
    return render_template("facility/profile.html", fac=fac, v=v, form=form, cities=cities)


# ---------------------------------------------------------------------- jobs

def _job_form(fac, job=None):
    specialties = query("SELECT id, name FROM specialties ORDER BY name")
    cities = query("SELECT ci.id, ci.name, ci.country_id, co.currency FROM cities ci JOIN countries co"
                   " ON co.id = ci.country_id WHERE co.active = 1 ORDER BY co.sort_order, ci.name")
    form = Form()
    if request.method == "POST":
        form.text("title", required=True, max_len=140, label=_("a job title"))
        form.choice("specialty_id", [(s["id"], s["name"]) for s in specialties], label=_("a specialty"))
        form.choice("grade", refdata.GRADES, label=_("a grade"))
        form.choice("city_id", [(c["id"], c["name"]) for c in cities], label=_("a city"))
        s = form.date("start_date", required=True, label=_("a start date"))
        e = form.date("end_date", required=True, label=_("an end date"))
        if s and e and e <= s:
            form.errors["end_date"] = _("The end date must be after the start date.")
        if s and not job and s < date.today().isoformat():
            form.errors["start_date"] = _("The start date can't be in the past.")
        form.integer("rate_amount", min_v=1, max_v=10_000_000)
        form.choice("rate_period", refdata.RATE_PERIODS)
        for perk in ("accommodation", "flights", "transport", "licensing_support"):
            form.flag(perk)
        form.text("description", required=True, max_len=5000, label=_("a description"))
        form.text("requirements", max_len=3000)
        if form.ok:
            c = form.clean
            city = next(x for x in cities if str(x["id"]) == c["city_id"])
            vals = (c["title"], int(c["specialty_id"]), c["grade"], city["country_id"], city["id"], c["start_date"],
                    c["end_date"], c["rate_amount"], city["currency"], c["rate_period"], c["accommodation"],
                    c["flights"], c["transport"], c["licensing_support"], c["description"], c["requirements"])
            if job:
                execute("UPDATE jobs SET title=?, specialty_id=?, grade=?, country_id=?, city_id=?, start_date=?,"
                        " end_date=?, rate_amount=?, rate_currency=?, rate_period=?, accommodation=?, flights=?,"
                        " transport=?, licensing_support=?, description=?, requirements=?, updated_at=datetime('now')"
                        " WHERE id=?", vals + (job["id"],))
                flash(_("Job updated."), "success")
                return redirect(url_for(".job", job_id=job["id"])), None
            jid = execute("INSERT INTO jobs (title, specialty_id, grade, country_id, city_id, start_date, end_date,"
                          " rate_amount, rate_currency, rate_period, accommodation, flights, transport,"
                          " licensing_support, description, requirements, facility_id)"
                          " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", vals + (g.user["id"],))
            mail.notify_admin("New job: %(title)s", "admin_new_job", {"title": c["title"]}, title=c["title"], facility=fac["name"],
                              verified=fac["verified"], job_id=jid)
            flash(_("Job published.") if fac["verified"] else
                  _("Job saved. It goes live as soon as we've verified your facility."), "success")
            return redirect(url_for(".job", job_id=jid)), None
        flash(_("Some details need attention. Check the highlighted fields."), "error")
    v = dict(job) if job else {"city_id": fac["city_id"], "rate_period": "month"}
    if request.method == "POST":
        v.update(form.clean)
    return None, render_template("facility/job_form.html", fac=fac, job=job, v=v, form=form,
                                 specialties=specialties, cities=cities)


@bp.route("/jobs/new", methods=["GET", "POST"])
@login_required("facility")
def new_job():
    redirect_resp, page = _job_form(get_facility(g.user["id"]))
    return redirect_resp or page


@bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required("facility")
def edit_job(job_id):
    redirect_resp, page = _job_form(get_facility(g.user["id"]), own_job(job_id))
    return redirect_resp or page


@bp.route("/jobs/<int:job_id>")
@login_required("facility")
def job(job_id):
    j = own_job(job_id)
    status = request.args.get("status", "")
    sql = ("SELECT a.*, d.title AS dtitle, d.first_name, d.last_name, d.grade, d.academic_rank, d.years_experience,"
           " d.qatar_license_status, d.current_country, d.available_from, s.name AS specialty FROM applications a"
           " JOIN doctors d ON d.user_id = a.doctor_id LEFT JOIN specialties s ON s.id = d.specialty_id"
           " WHERE a.job_id = ?")
    args = [job_id]
    if status:
        sql += " AND a.status = ?"
        args.append(status)
    else:
        sql += " AND a.status != 'withdrawn'"
    apps = query(sql + " ORDER BY a.created_at DESC", args)
    counts = {r["status"]: r["n"] for r in query(
        "SELECT status, COUNT(*) AS n FROM applications WHERE job_id = ? GROUP BY status", (job_id,))}
    return render_template("facility/job.html", job=j, apps=apps, counts=counts, status=status,
                           fac=get_facility(g.user["id"]))


@bp.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required("facility")
def job_status(job_id):
    own_job(job_id)
    status = request.form.get("status")
    if status not in dict(refdata.JOB_STATUSES):
        abort(400)
    execute("UPDATE jobs SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, job_id))
    flash({"open": "Job reopened.", "filled": "Job marked as filled.", "closed": "Job closed."}[status], "success")
    return redirect(url_for(".job", job_id=job_id))


@bp.route("/applications/<int:app_id>/status", methods=["POST"])
@login_required("facility")
def application_status(app_id):
    a = query("SELECT a.*, j.title, j.facility_id FROM applications a JOIN jobs j ON j.id = a.job_id"
              " WHERE a.id = ? AND j.facility_id = ?", (app_id, g.user["id"]), one=True)
    if not a:
        abort(404)
    status = request.form.get("status")
    allowed = [k for k, _ in refdata.APPLICATION_STATUSES if k not in ("withdrawn",)]
    if status not in allowed or a["status"] == "withdrawn":
        abort(400)
    if status != a["status"]:
        execute("UPDATE applications SET status = ?, updated_at = datetime('now') WHERE id = ?", (status, app_id))
        d = query("SELECT d.first_name, d.last_name, u.email, u.lang FROM doctors d JOIN users u ON u.id = d.user_id"
                  " WHERE d.user_id = ?", (a["doctor_id"],), one=True)
        fac = get_facility(g.user["id"])
        mail.send(d["email"], "Update on your application: %(title)s", "doctor_status_change", d["lang"],
                  {"title": a["title"]}, doctor=d, job_title=a["title"], facility=fac["name"], status=status)
        flash(_("Dr %(name)s moved to: %(status)s. They've been emailed.", name=d["last_name"],
                status=refdata.label(refdata.APPLICATION_STATUSES, status)), "success")
    return redirect(request.form.get("back") or url_for(".job", job_id=a["job_id"]))


# ------------------------------------------------------------------- doctors

@bp.route("/doctors")
@login_required("facility")
def doctors():
    fac = get_facility(g.user["id"])
    specialties = query("SELECT id, name FROM specialties ORDER BY name")
    f = {k: request.args.get(k, "").strip() for k in ("specialty", "grade", "academic", "licence", "available", "q")}
    rows, total, page, per = [], 0, 1, 20
    if fac["verified"]:
        where = ["d.visible_to_facilities = 1", "u.is_active = 1"]
        args = []
        if f["specialty"].isdigit():
            where.append("d.specialty_id = ?")
            args.append(int(f["specialty"]))
        if f["grade"]:
            where.append("d.grade = ?")
            args.append(f["grade"])
        if f["academic"] == "any":
            where.append("d.academic_rank != ''")
        elif f["academic"].isdigit():
            keys = refdata.academic_keys_at_least(int(f["academic"]))
            where.append("d.academic_rank IN (" + ",".join("?" * len(keys)) + ")")
            args += keys
        if f["licence"] == "any_progress":
            where.append("d.qatar_license_status != 'none'")
        elif f["licence"]:
            where.append("d.qatar_license_status = ?")
            args.append(f["licence"])
        if f["available"]:
            where.append("d.available_from IS NOT NULL AND d.available_from <= ? AND"
                         " (d.available_to IS NULL OR d.available_to >= ?)")
            args += [f["available"], f["available"]]
        if f["q"]:
            where.append("(d.first_name || ' ' || d.last_name LIKE ? OR d.subspecialty LIKE ? OR d.qualifications LIKE ?"
                         " OR d.medical_school LIKE ?)")
            args += [f"%{f['q']}%"] * 4
        w = " WHERE " + " AND ".join(where)
        page, per, offset = page_args(20)
        total = query("SELECT COUNT(*) AS n FROM doctors d JOIN users u ON u.id = d.user_id" + w, args, one=True)["n"]
        rows = query(DOCTOR_SELECT + w + " ORDER BY d.verified DESC, d.updated_at DESC LIMIT ? OFFSET ?",
                     args + [per, offset])
    return render_template("facility/doctors.html", fac=fac, rows=rows, total=total, f=f, page=page, per=per,
                           specialties=specialties)


@bp.route("/doctors/<int:doctor_id>")
@login_required("facility")
def doctor(doctor_id):
    fac = get_facility(g.user["id"])
    if not can_view_doctor(fac, doctor_id):
        abort(404)
    d = query(DOCTOR_SELECT + " WHERE d.user_id = ?", (doctor_id,), one=True)
    if not d:
        abort(404)
    docs = query("SELECT * FROM documents WHERE user_id = ? ORDER BY kind = 'cv' DESC, created_at DESC", (doctor_id,))
    apps = query("SELECT a.*, j.title FROM applications a JOIN jobs j ON j.id = a.job_id"
                 " WHERE a.doctor_id = ? AND j.facility_id = ? ORDER BY a.created_at DESC", (doctor_id, g.user["id"]))
    open_jobs = query("SELECT id, title FROM jobs WHERE facility_id = ? AND status = 'open' ORDER BY start_date",
                      (g.user["id"],))
    invites = query("SELECT i.*, j.title FROM invitations i LEFT JOIN jobs j ON j.id = i.job_id"
                    " WHERE i.facility_id = ? AND i.doctor_id = ? ORDER BY i.created_at DESC", (g.user["id"], doctor_id))
    return render_template("facility/doctor.html", fac=fac, d=d, docs=docs, apps=apps, open_jobs=open_jobs,
                           invites=invites)


@bp.route("/doctors/<int:doctor_id>/invite", methods=["POST"])
@login_required("facility")
def invite(doctor_id):
    fac = get_facility(g.user["id"])
    if not fac["verified"] or not can_view_doctor(fac, doctor_id):
        abort(403)
    job_id = request.form.get("job_id") or None
    job = None
    if job_id:
        job = query("SELECT * FROM jobs WHERE id = ? AND facility_id = ? AND status = 'open'",
                    (job_id, g.user["id"]), one=True)
        if not job:
            abort(400)
    message = (request.form.get("message") or "").strip()[:2000]
    if query("SELECT 1 FROM invitations WHERE facility_id = ? AND doctor_id = ? AND IFNULL(job_id, 0) = ? AND status = 'sent'",
             (g.user["id"], doctor_id, int(job_id or 0)), one=True):
        flash(_("You've already sent this doctor an invitation that's waiting for a reply."), "info")
        return redirect(url_for(".doctor", doctor_id=doctor_id))
    execute("INSERT INTO invitations (facility_id, doctor_id, job_id, message) VALUES (?, ?, ?, ?)",
            (g.user["id"], doctor_id, job["id"] if job else None, message))
    d = query("SELECT d.first_name, d.last_name, u.email, u.lang FROM doctors d JOIN users u ON u.id = d.user_id"
              " WHERE d.user_id = ?", (doctor_id,), one=True)
    mail.send(d["email"], "%(facility)s invited you to a locum role", "doctor_invited", d["lang"],
              {"facility": fac["name"]}, doctor=d, facility=fac["name"], job=job, message=message)
    flash(_("Invitation sent to Dr %(name)s.", name=d["last_name"]), "success")
    return redirect(url_for(".doctor", doctor_id=doctor_id))
