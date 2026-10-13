from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import analytics, db, mail, refdata, storage, store, world
from ..i18n import _
from ..db import get_doctor, public_jobs
from ..security import login_required
from . import Form

bp = Blueprint("doctor", __name__, url_prefix="/doctor")

PROFILE_FIELDS = ("phone", "nationality", "current_country", "medical_school", "qualifications", "primary_license")


def profile_readiness(uid):
    d = get_doctor(uid)
    has_cv = d["cv_count"] > 0
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
    apps = [db.application_full(a) for a in
            db.newest_first(store.find("applications", doctor_id=g.user["id"]), "updated_at")[:5]]
    invites = [db.invitation_full(i) for i in
               db.newest_first(store.find("invitations", doctor_id=g.user["id"], status="sent"))]
    spec = d["specialty_id"]
    matches = public_jobs(lambda j: j["specialty_id"] == spec, limit=4) if spec else []
    return render_template("doctor/dashboard.html", d=d, apps=apps, invites=invites, matches=matches,
                           readiness=profile_readiness(g.user["id"]))


@bp.route("/profile", methods=["GET", "POST"])
@login_required("doctor")
def profile():
    d = get_doctor(g.user["id"])
    specialties = db.specialties()
    countries = db.countries()
    form = Form()
    if request.method == "POST":
        form.choice("title", [("Dr", "Dr"), ("Prof", "Prof"), ("Mr", "Mr"), ("Ms", "Ms")])
        form.text("first_name", required=True, max_len=80, label=_("your first name"))
        form.text("last_name", required=True, max_len=80, label=_("your last name"))
        form.phone()
        countries_all = [(n, n) for _c, n in world.WORLD]
        form.choice("nationality", countries_all, label=_("your nationality"))
        form.choice("current_country", countries_all, label=_("your country of residence"))
        form.choice("specialty_id", [(s["id"], s["name"]) for s in specialties], label=_("your specialty"))
        form.text("subspecialty", max_len=120)
        form.choice("grade", refdata.GRADES, label=_("your grade"))
        form.choice("academic_rank", refdata.ACADEMIC_RANKS, required=False)
        form.integer("years_experience", required=True, min_v=0, max_v=60, label=_("years of experience"))
        form.text("medical_school", required=True, max_len=160, label=_("the university you graduated from"))
        form.integer("graduation_year", min_v=1950, max_v=date.today().year, label=_("your graduation year"))
        form.text("qualifications", required=True, max_len=300, label=_("your qualifications"))
        form.text("primary_license", required=True, max_len=200, label=_("your current licence"))
        form.choice("qatar_license_status", refdata.QATAR_LICENSE_STATUS)
        form.choice("exam_status", refdata.EXAM_STATUS)
        form.flag("has_psv")
        form.flag("good_standing")
        form.text("languages", required=True, max_len=200, label=_("the languages you speak"))
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
            fields = {k: c[k] for k in (
                "title", "first_name", "last_name", "phone", "nationality", "current_country", "specialty_id",
                "subspecialty", "grade", "academic_rank", "years_experience", "medical_school", "graduation_year",
                "qualifications", "primary_license", "has_psv", "good_standing", "languages", "available_from",
                "available_to", "min_weeks", "bio", "visible_to_facilities")}
            fields.update(qatar_license_status=c["qatar_license_status"] or "none",
                          exam_status=c["exam_status"] or "unknown", preferred_countries=",".join(prefs) or "QA",
                          updated_at=store.now())
            store.update("doctors", g.user["id"], **fields)
            flash(_("Profile saved."), "success")
            if not profile_readiness(g.user["id"])["ready"]:
                return redirect(url_for(".documents"))
            return redirect(url_for(".dashboard"))
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
        count = store.count("documents", user_id=g.user["id"])
        if count >= 20:
            flash(_("You can store up to 20 documents. Delete one to add another."), "error")
            return redirect(url_for(".documents"))
        try:
            name, original, mime, size = storage.save(request.files.get("file"))
        except storage.UploadError as e:
            flash(str(e), "error")
            return redirect(url_for(".documents"))
        store.add("documents", {"user_id": g.user["id"], "kind": kind, "original_name": original,
                                "storage_name": name, "mime_type": mime, "size_bytes": size})
        store.update("doctors", g.user["id"], updated_at=store.now())
        flash(_("%(kind)s uploaded.", kind=refdata.label(refdata.DOCUMENT_KINDS, kind)), "success")
        return redirect(url_for(".documents"))
    docs = db.documents_for(g.user["id"])
    return render_template("doctor/documents.html", docs=docs, readiness=profile_readiness(g.user["id"]))


@bp.route("/documents/<doc_id>/delete", methods=["POST"])
@login_required("doctor")
def delete_document(doc_id):
    doc = store.get("documents", doc_id)
    if not doc or doc["user_id"] != g.user["id"]:
        abort(404)
    storage.delete(doc["storage_name"])
    store.delete("documents", doc_id)
    flash(_("%(name)s deleted.", name=doc["original_name"]), "info")
    return redirect(url_for(".documents"))


@bp.route("/applications")
@login_required("doctor")
def applications():
    apps = [db.application_full(a) for a in db.newest_first(store.find("applications", doctor_id=g.user["id"]))]
    invites = [db.invitation_full(i) for i in db.newest_first(store.find("invitations", doctor_id=g.user["id"]))]
    return render_template("doctor/applications.html", apps=apps, invites=invites)


@bp.route("/jobs/<job_id>/apply", methods=["POST"])
@login_required("doctor")
def apply(job_id):
    job = db.get_job(job_id)
    if not job or not (job["status"] == "open" and job["facility_verified"] and job["country_active"]):
        abort(404)
    if not profile_readiness(g.user["id"])["ready"]:
        flash(_("Complete your profile and upload your CV before applying."), "error")
        return redirect(url_for("public.job", job_id=job_id))
    if store.first("applications", job_id=job_id, doctor_id=g.user["id"]):
        flash(_("You've already applied for this job."), "info")
        return redirect(url_for("public.job", job_id=job_id))
    note = (request.form.get("cover_note") or "").strip()[:3000]
    # One application per doctor per job: the id makes a second click a no-op.
    app_id = f"{job_id}_{g.user['id']}"
    store.create("applications", app_id, {"job_id": job_id, "doctor_id": g.user["id"], "cover_note": note})
    d = get_doctor(g.user["id"])
    fac_user = store.get("users", job["facility_id"])
    ctx = dict(job=job, doctor=d, note=note)
    title = {"title": job["title"]}
    mail.send(fac_user["email"], "New applicant: %(title)s", "facility_new_application", fac_user["lang"], title, **ctx)
    mail.notify_admin("Application: Dr %(name)s for %(title)s", "facility_new_application",
                      {"name": d["last_name"], "title": job["title"]}, **ctx)
    mail.send(d["email"], "Application sent: %(title)s", "doctor_applied", d["lang"], title, **ctx)
    analytics.track("job_application", specialty=job["specialty"] or "", grade=job["grade"] or "")
    return redirect(url_for(".application_sent", app_id=app_id))


@bp.route("/applications/<app_id>/sent")
@login_required("doctor")
def application_sent(app_id):
    """Thank-you page after applying: what happens next, and similar jobs."""
    a = store.get("applications", app_id)
    if not a or a["doctor_id"] != g.user["id"]:
        abort(404)
    job = db.get_job(a["job_id"])
    applied = {x["job_id"] for x in store.find("applications", doctor_id=g.user["id"])}
    similar = public_jobs(lambda j: j["specialty_id"] == job["specialty_id"] and j["id"] not in applied, limit=3) if job else []
    return render_template("public/thanks.html", kind="application", job=job, similar=similar)


@bp.route("/applications/<app_id>/withdraw", methods=["POST"])
@login_required("doctor")
def withdraw(app_id):
    a = store.get("applications", app_id)
    if not a or a["doctor_id"] != g.user["id"]:
        abort(404)
    if a["status"] in ("placed", "withdrawn"):
        flash(_("This application can no longer be withdrawn."), "error")
    else:
        store.update("applications", app_id, status="withdrawn", updated_at=store.now())
        flash(_("Application withdrawn."), "info")
    return redirect(url_for(".applications"))


@bp.route("/invitations/<inv_id>", methods=["POST"])
@login_required("doctor")
def respond_invitation(inv_id):
    inv = store.get("invitations", inv_id)
    if not inv or inv["doctor_id"] != g.user["id"] or inv["status"] != "sent":
        abort(404)
    answer = request.form.get("answer")
    if answer not in ("accepted", "declined"):
        abort(400)
    store.update("invitations", inv_id, status=answer)
    fac = db.get_facility(inv["facility_id"])
    d = get_doctor(g.user["id"])
    subject = "Dr %(name)s accepted your invitation" if answer == "accepted" else "Dr %(name)s declined your invitation"
    mail.send(fac["email"], subject, "facility_invite_answer", fac["lang"], {"name": d["last_name"]},
              doctor=d, answer=answer, facility=fac["name"])
    if answer == "accepted" and inv["job_id"]:
        if profile_readiness(g.user["id"])["ready"]:
            store.create("applications", f"{inv['job_id']}_{g.user['id']}",
                         {"job_id": inv["job_id"], "doctor_id": g.user["id"], "cover_note": "Accepted invitation",
                          "status": "shortlisted"})
            flash(_("Invitation accepted. You've been added to the shortlist for this job."), "success")
        else:
            flash(_("Invitation accepted. Finish your profile and CV so the facility can review you."), "success")
    else:
        flash(_("Invitation declined."), "info")
    return redirect(url_for(".applications"))
