from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import mail, refdata, storage
from ..i18n import _
from ..db import execute, get_db, query
from ..security import login_required
from . import Form
from .public import JOB_SELECT, public_jobs

bp = Blueprint("doctor", __name__, url_prefix="/doctor")

PROFILE_FIELDS = ("phone", "nationality", "current_country", "qualifications", "primary_license")


def get_doctor(uid):
    return query(
        "SELECT d.*, u.email, u.lang, s.name AS specialty FROM doctors d JOIN users u ON u.id = d.user_id"
        " LEFT JOIN specialties s ON s.id = d.specialty_id WHERE d.user_id = ?", (uid,), one=True)


def profile_readiness(uid):
    d = get_doctor(uid)
    has_cv = query("SELECT 1 FROM documents WHERE user_id = ? AND kind = 'cv'", (uid,), one=True) is not None
    profile_done = all(d[f] for f in PROFILE_FIELDS) and d["years_experience"] is not None
    items = [
        (_("Complete your professional profile"), profile_done, url_for("doctor.profile")),
        (_("Upload your CV"), has_cv, url_for("doctor.documents")),
        (_("Add your availability"), bool(d["available_from"]), url_for("doctor.profile") + "#availability"),
    ]
    return {"items": items, "ready": profile_done and has_cv, "done": sum(1 for _, ok, _ in items if ok)}


@bp.route("/")
@login_required("doctor")
def dashboard():
    d = get_doctor(g.user["id"])
    apps = query(
        "SELECT a.*, j.title, j.start_date, j.end_date, f.name AS facility, ci.name AS city FROM applications a"
        " JOIN jobs j ON j.id = a.job_id JOIN facilities f ON f.user_id = j.facility_id"
        " LEFT JOIN cities ci ON ci.id = j.city_id WHERE a.doctor_id = ? ORDER BY a.updated_at DESC LIMIT 5",
        (g.user["id"],))
    invites = query(
        "SELECT i.*, f.name AS facility, j.title AS job_title FROM invitations i"
        " JOIN facilities f ON f.user_id = i.facility_id LEFT JOIN jobs j ON j.id = i.job_id"
        " WHERE i.doctor_id = ? AND i.status = 'sent' ORDER BY i.created_at DESC", (g.user["id"],))
    matches = public_jobs("j.specialty_id = ?", (d["specialty_id"],), limit=4) if d["specialty_id"] else []
    return render_template("doctor/dashboard.html", d=d, apps=apps, invites=invites, matches=matches,
                           readiness=profile_readiness(g.user["id"]))


@bp.route("/profile", methods=["GET", "POST"])
@login_required("doctor")
def profile():
    d = get_doctor(g.user["id"])
    specialties = query("SELECT id, name FROM specialties ORDER BY name")
    countries = query("SELECT code, name, active FROM countries ORDER BY sort_order")
    form = Form()
    if request.method == "POST":
        form.choice("title", [("Dr", "Dr"), ("Prof", "Prof"), ("Mr", "Mr"), ("Ms", "Ms")])
        form.text("first_name", required=True, max_len=80, label=_("your first name"))
        form.text("last_name", required=True, max_len=80, label=_("your last name"))
        form.text("phone", required=True, max_len=40, label=_("a phone number"))
        form.text("nationality", required=True, max_len=80, label=_("your nationality"))
        form.text("current_country", required=True, max_len=80, label=_("where you live now"))
        form.choice("specialty_id", [(s["id"], s["name"]) for s in specialties], label=_("your specialty"))
        form.text("subspecialty", max_len=120)
        form.choice("grade", refdata.GRADES, label=_("your grade"))
        form.integer("years_experience", required=True, min_v=0, max_v=60, label=_("years of experience"))
        form.text("qualifications", required=True, max_len=300, label=_("your qualifications"))
        form.text("primary_license", required=True, max_len=200, label=_("your current licence"))
        form.choice("qatar_license_status", refdata.QATAR_LICENSE_STATUS)
        form.choice("exam_status", refdata.EXAM_STATUS)
        form.flag("has_psv")
        form.flag("good_standing")
        form.text("languages", max_len=200)
        start = form.date("available_from")
        end = form.date("available_to")
        if start and end and end < start:
            form.errors["available_to"] = _("The end date must be after the start date.")
        form.integer("min_weeks", min_v=1, max_v=104)
        prefs = [c for c in request.form.getlist("preferred_countries") if c in {x["code"] for x in countries}]
        form.text("bio", max_len=2000)
        form.flag("visible_to_facilities")
        if form.ok:
            c = form.clean
            execute(
                "UPDATE doctors SET title=?, first_name=?, last_name=?, phone=?, nationality=?, current_country=?,"
                " specialty_id=?, subspecialty=?, grade=?, years_experience=?, qualifications=?, primary_license=?,"
                " qatar_license_status=?, exam_status=?, has_psv=?, good_standing=?, languages=?, available_from=?,"
                " available_to=?, min_weeks=?, preferred_countries=?, bio=?, visible_to_facilities=?,"
                " updated_at=datetime('now') WHERE user_id=?",
                (c["title"], c["first_name"], c["last_name"], c["phone"], c["nationality"], c["current_country"],
                 int(c["specialty_id"]), c["subspecialty"], c["grade"], c["years_experience"], c["qualifications"],
                 c["primary_license"], c["qatar_license_status"] or "none", c["exam_status"] or "unknown",
                 c["has_psv"], c["good_standing"], c["languages"], c["available_from"], c["available_to"],
                 c["min_weeks"], ",".join(prefs) or "QA", c["bio"], c["visible_to_facilities"], g.user["id"]),
            )
            flash(_("Profile saved."), "success")
            if not profile_readiness(g.user["id"])["ready"]:
                return redirect(url_for(".documents"))
            return redirect(url_for(".dashboard"))
        flash(_("Some details need attention. Check the highlighted fields."), "error")
    values = dict(d)
    if request.method == "POST":
        values.update(form.clean)
        values["preferred_countries"] = ",".join(request.form.getlist("preferred_countries"))
    return render_template("doctor/profile.html", d=d, v=values, form=form, specialties=specialties,
                           countries=countries)


@bp.route("/documents", methods=["GET", "POST"])
@login_required("doctor")
def documents():
    if request.method == "POST":
        kind = request.form.get("kind", "")
        if kind not in dict(refdata.DOCUMENT_KINDS):
            flash(_("Choose what kind of document this is."), "error")
            return redirect(url_for(".documents"))
        count = query("SELECT COUNT(*) AS n FROM documents WHERE user_id = ?", (g.user["id"],), one=True)["n"]
        if count >= 20:
            flash(_("You can store up to 20 documents. Delete one to add another."), "error")
            return redirect(url_for(".documents"))
        try:
            name, original, mime, size = storage.save(request.files.get("file"))
        except storage.UploadError as e:
            flash(str(e), "error")
            return redirect(url_for(".documents"))
        execute("INSERT INTO documents (user_id, kind, original_name, storage_name, mime_type, size_bytes)"
                " VALUES (?, ?, ?, ?, ?, ?)", (g.user["id"], kind, original, name, mime, size))
        execute("UPDATE doctors SET updated_at = datetime('now') WHERE user_id = ?", (g.user["id"],))
        flash(_("%(kind)s uploaded.", kind=refdata.label(refdata.DOCUMENT_KINDS, kind)), "success")
        return redirect(url_for(".documents"))
    docs = query("SELECT * FROM documents WHERE user_id = ? ORDER BY kind = 'cv' DESC, created_at DESC",
                 (g.user["id"],))
    return render_template("doctor/documents.html", docs=docs, readiness=profile_readiness(g.user["id"]))


@bp.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required("doctor")
def delete_document(doc_id):
    doc = query("SELECT * FROM documents WHERE id = ? AND user_id = ?", (doc_id, g.user["id"]), one=True)
    if not doc:
        abort(404)
    storage.delete(doc["storage_name"])
    execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    flash(_("%(name)s deleted.", name=doc["original_name"]), "info")
    return redirect(url_for(".documents"))


@bp.route("/applications")
@login_required("doctor")
def applications():
    apps = query(
        "SELECT a.*, j.title, j.start_date, j.end_date, j.rate_amount, j.rate_currency, j.rate_period,"
        " j.status AS job_status, f.name AS facility, ci.name AS city FROM applications a"
        " JOIN jobs j ON j.id = a.job_id JOIN facilities f ON f.user_id = j.facility_id"
        " LEFT JOIN cities ci ON ci.id = j.city_id WHERE a.doctor_id = ? ORDER BY a.created_at DESC",
        (g.user["id"],))
    invites = query(
        "SELECT i.*, f.name AS facility, j.title AS job_title FROM invitations i"
        " JOIN facilities f ON f.user_id = i.facility_id LEFT JOIN jobs j ON j.id = i.job_id"
        " WHERE i.doctor_id = ? ORDER BY i.created_at DESC", (g.user["id"],))
    return render_template("doctor/applications.html", apps=apps, invites=invites)


@bp.route("/jobs/<int:job_id>/apply", methods=["POST"])
@login_required("doctor")
def apply(job_id):
    job = query(JOB_SELECT + " WHERE j.id = ? AND j.status = 'open' AND f.verified = 1 AND co.active = 1",
                (job_id,), one=True)
    if not job:
        abort(404)
    if not profile_readiness(g.user["id"])["ready"]:
        flash(_("Complete your profile and upload your CV before applying."), "error")
        return redirect(url_for("public.job", job_id=job_id))
    if query("SELECT 1 FROM applications WHERE job_id = ? AND doctor_id = ?", (job_id, g.user["id"]), one=True):
        flash(_("You've already applied for this job."), "info")
        return redirect(url_for("public.job", job_id=job_id))
    note = (request.form.get("cover_note") or "").strip()[:3000]
    execute("INSERT INTO applications (job_id, doctor_id, cover_note) VALUES (?, ?, ?)", (job_id, g.user["id"], note))
    d = get_doctor(g.user["id"])
    fac_user = query("SELECT email, lang FROM users WHERE id = ?", (job["facility_id"],), one=True)
    ctx = dict(job=job, doctor=d, note=note)
    title = {"title": job["title"]}
    mail.send(fac_user["email"], "New applicant: %(title)s", "facility_new_application", fac_user["lang"], title, **ctx)
    mail.notify_admin("Application: Dr %(name)s for %(title)s", "facility_new_application",
                      {"name": d["last_name"], "title": job["title"]}, **ctx)
    mail.send(d["email"], "Application sent: %(title)s", "doctor_applied", d["lang"], title, **ctx)
    flash(_("Application sent. The facility will see your profile and CV, and you'll get an email when your status changes."),
          "success")
    return redirect(url_for(".applications"))


@bp.route("/applications/<int:app_id>/withdraw", methods=["POST"])
@login_required("doctor")
def withdraw(app_id):
    a = query("SELECT * FROM applications WHERE id = ? AND doctor_id = ?", (app_id, g.user["id"]), one=True)
    if not a:
        abort(404)
    if a["status"] in ("placed", "withdrawn"):
        flash(_("This application can no longer be withdrawn."), "error")
    else:
        execute("UPDATE applications SET status = 'withdrawn', updated_at = datetime('now') WHERE id = ?", (app_id,))
        flash(_("Application withdrawn."), "info")
    return redirect(url_for(".applications"))


@bp.route("/invitations/<int:inv_id>", methods=["POST"])
@login_required("doctor")
def respond_invitation(inv_id):
    inv = query("SELECT * FROM invitations WHERE id = ? AND doctor_id = ?", (inv_id, g.user["id"]), one=True)
    if not inv or inv["status"] != "sent":
        abort(404)
    answer = request.form.get("answer")
    if answer not in ("accepted", "declined"):
        abort(400)
    db = get_db()
    db.execute("UPDATE invitations SET status = ? WHERE id = ?", (answer, inv_id))
    db.commit()
    fac = query("SELECT f.name, u.email, u.lang FROM facilities f JOIN users u ON u.id = f.user_id WHERE f.user_id = ?",
                (inv["facility_id"],), one=True)
    d = get_doctor(g.user["id"])
    subject = "Dr %(name)s accepted your invitation" if answer == "accepted" else "Dr %(name)s declined your invitation"
    mail.send(fac["email"], subject, "facility_invite_answer", fac["lang"], {"name": d["last_name"]},
              doctor=d, answer=answer, facility=fac["name"])
    if answer == "accepted" and inv["job_id"]:
        if profile_readiness(g.user["id"])["ready"]:
            db.execute("INSERT OR IGNORE INTO applications (job_id, doctor_id, cover_note, status)"
                       " VALUES (?, ?, 'Accepted invitation', 'shortlisted')", (inv["job_id"], g.user["id"]))
            db.commit()
            flash(_("Invitation accepted. You've been added to the shortlist for this job."), "success")
        else:
            flash(_("Invitation accepted. Finish your profile and CV so the facility can review you."), "success")
    else:
        flash(_("Invitation declined."), "info")
    return redirect(url_for(".applications"))
