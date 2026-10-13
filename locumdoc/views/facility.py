from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .. import analytics, db, mail, refdata, store
from ..i18n import _
from ..db import get_doctor, get_facility
from ..security import login_required
from . import Form, page_args

bp = Blueprint("facility", __name__, url_prefix="/facility")


def own_job(job_id):
    job = db.get_job(job_id)
    if not job or job["facility_id"] != g.user["id"]:
        abort(404)
    return job


def facility_applications(fac_id):
    """Every application to any of this facility's jobs."""
    out = []
    for j in store.find("jobs", facility_id=fac_id):
        out += store.find("applications", job_id=j["id"])
    return out


def can_view_doctor(fac, doctor_id):
    if any(a["doctor_id"] == doctor_id and a["status"] != "withdrawn" for a in facility_applications(fac["id"])):
        return True
    d = store.get("doctors", doctor_id)
    return bool(fac["verified"] and d and d["visible_to_facilities"])


@bp.route("/")
@login_required("facility")
def dashboard():
    fac = get_facility(g.user["id"])
    jobs = []
    for j in store.find("jobs", facility_id=g.user["id"]):
        apps = store.find("applications", job_id=j["id"])
        jobs.append(dict(j, specialty=db.specialty_name(j["specialty_id"]),
                         applicants=sum(1 for a in apps if a["status"] != "withdrawn"),
                         new_count=sum(1 for a in apps if a["status"] == "submitted")))
    jobs.sort(key=lambda j: (j["status"] != "open", j["start_date"]))
    recent = [db.application_full(a) for a in
              db.newest_first([a for a in facility_applications(g.user["id"]) if a["status"] != "withdrawn"])[:8]]
    return render_template("facility/dashboard.html", fac=fac, jobs=jobs, recent=recent)


@bp.route("/profile", methods=["GET", "POST"])
@login_required("facility")
def profile():
    fac = get_facility(g.user["id"])
    cities = db.cities(active_only=True, include=fac["city_id"])
    form = Form()
    if request.method == "POST":
        form.text("name", required=True, max_len=160, label=_("the facility name"))
        form.choice("facility_type", refdata.FACILITY_TYPES)
        form.choice("sector", refdata.SECTORS)
        form.choice("city_id", [(c["id"], c["name"]) for c in cities], label=_("a city"))
        form.text("website", max_len=200)
        form.text("contact_name", required=True, max_len=120, label=_("a contact name"))
        form.text("contact_role", max_len=120)
        form.phone()
        form.text("about", max_len=2000)
        if form.ok:
            c = form.clean
            city = store.get("cities", c["city_id"])
            store.update("facilities", g.user["id"], country_id=city["country_id"], city_id=city["id"],
                         updated_at=store.now(), **{k: c[k] for k in (
                             "name", "facility_type", "sector", "website", "contact_name", "contact_role", "phone",
                             "about")})
            flash(_("Facility profile saved."), "success")
            return redirect(url_for(".dashboard"))
    v = dict(fac)
    if request.method == "POST":
        v.update(form.clean)
    return render_template("facility/profile.html", fac=fac, v=v, form=form, cities=cities)


# ---------------------------------------------------------------------- jobs

def _job_form(fac, job=None):
    specialties = db.specialties()
    cities = db.cities(active_only=True)
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
            vals = {k: c[k] for k in ("title", "specialty_id", "grade", "start_date", "end_date", "rate_amount",
                                      "rate_period", "accommodation", "flights", "transport", "licensing_support",
                                      "description", "requirements")}
            vals.update(country_id=city["country_id"], city_id=city["id"], rate_currency=city["currency"])
            if job:
                store.update("jobs", job["id"], updated_at=store.now(), **vals)
                flash(_("Job updated."), "success")
                return redirect(url_for(".job", job_id=job["id"])), None
            jid = store.add("jobs", dict(vals, facility_id=g.user["id"]))
            analytics.track("job_posted", specialty=db.specialty_name(vals["specialty_id"]) or "")
            mail.notify_admin("New job: %(title)s", "admin_new_job", {"title": c["title"]}, title=c["title"], facility=fac["name"],
                              verified=fac["verified"], job_id=jid)
            flash(_("Job published.") if fac["verified"] else
                  _("Job saved. It goes live as soon as we've verified your facility."), "success")
            return redirect(url_for(".job", job_id=jid)), None
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


@bp.route("/jobs/<job_id>/edit", methods=["GET", "POST"])
@login_required("facility")
def edit_job(job_id):
    redirect_resp, page = _job_form(get_facility(g.user["id"]), own_job(job_id))
    return redirect_resp or page


@bp.route("/jobs/<job_id>")
@login_required("facility")
def job(job_id):
    j = own_job(job_id)
    status = request.args.get("status", "")
    all_apps = store.find("applications", job_id=job_id)
    shown = [a for a in all_apps if (a["status"] == status if status else a["status"] != "withdrawn")]
    apps = [db.application_full(a) for a in db.newest_first(shown)]
    counts = {}
    for a in all_apps:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    return render_template("facility/job.html", job=j, apps=apps, counts=counts, status=status,
                           fac=get_facility(g.user["id"]))


@bp.route("/jobs/<job_id>/status", methods=["POST"])
@login_required("facility")
def job_status(job_id):
    own_job(job_id)
    status = request.form.get("status")
    if status not in dict(refdata.JOB_STATUSES):
        abort(400)
    store.update("jobs", job_id, status=status, updated_at=store.now())
    flash({"open": "Job reopened.", "filled": "Job marked as filled.", "closed": "Job closed."}[status], "success")
    return redirect(url_for(".job", job_id=job_id))


@bp.route("/applications/<app_id>/status", methods=["POST"])
@login_required("facility")
def application_status(app_id):
    a = store.get("applications", app_id)
    j = store.get("jobs", a["job_id"]) if a else None
    if not a or not j or j["facility_id"] != g.user["id"]:
        abort(404)
    status = request.form.get("status")
    allowed = [k for k, _ in refdata.APPLICATION_STATUSES if k not in ("withdrawn",)]
    if status not in allowed or a["status"] == "withdrawn":
        abort(400)
    if status != a["status"]:
        store.update("applications", app_id, status=status, updated_at=store.now())
        d = get_doctor(a["doctor_id"])
        fac = get_facility(g.user["id"])
        mail.send(d["email"], "Update on your application: %(title)s", "doctor_status_change", d["lang"],
                  {"title": j["title"]}, doctor=d, job_title=j["title"], facility=fac["name"], status=status)
        flash(_("Dr %(name)s moved to: %(status)s. They've been emailed.", name=d["last_name"],
                status=refdata.label(refdata.APPLICATION_STATUSES, status)), "success")
    return redirect(request.form.get("back") or url_for(".job", job_id=a["job_id"]))


# ------------------------------------------------------------------- doctors

def _contains(text, q):
    return q.casefold() in (text or "").casefold()


@bp.route("/doctors")
@login_required("facility")
def doctors():
    fac = get_facility(g.user["id"])
    specialties = db.specialties()
    f = {k: request.args.get(k, "").strip() for k in ("specialty", "grade", "academic", "licence", "available", "q")}
    rows, total, page, per = [], 0, 1, 20
    if fac["verified"]:
        tests = []
        if f["specialty"]:
            tests.append(lambda d: d["specialty_id"] == f["specialty"])
        if f["grade"]:
            tests.append(lambda d: d["grade"] == f["grade"])
        if f["academic"] == "any":
            tests.append(lambda d: d["academic_rank"] != "")
        elif f["academic"].isdigit():
            keys = set(refdata.academic_keys_at_least(int(f["academic"])))
            tests.append(lambda d: d["academic_rank"] in keys)
        if f["licence"] == "any_progress":
            tests.append(lambda d: d["qatar_license_status"] != "none")
        elif f["licence"]:
            tests.append(lambda d: d["qatar_license_status"] == f["licence"])
        if f["available"]:
            day = f["available"]
            tests.append(lambda d: bool(d["available_from"]) and d["available_from"] <= day
                         and (not d["available_to"] or d["available_to"] >= day))
        if f["q"]:
            q = f["q"]
            tests.append(lambda d: any(_contains(x, q) for x in (
                f"{d['first_name']} {d['last_name']}", d["subspecialty"], d["qualifications"], d["medical_school"])))
        matching = []
        for d in store.find("doctors", visible_to_facilities=1):
            u = store.get("users", d["id"])
            if u and u["is_active"] and all(t(d) for t in tests):
                matching.append(d)
        matching.sort(key=lambda d: (d["verified"], d["updated_at"] or ""), reverse=True)
        page, per, offset = page_args(20)
        total = len(matching)
        rows = [db.doctor_full(d) for d in matching[offset:offset + per]]
    return render_template("facility/doctors.html", fac=fac, rows=rows, total=total, f=f, page=page, per=per,
                           specialties=specialties)


@bp.route("/doctors/<doctor_id>")
@login_required("facility")
def doctor(doctor_id):
    fac = get_facility(g.user["id"])
    if not can_view_doctor(fac, doctor_id):
        abort(404)
    d = get_doctor(doctor_id)
    if not d:
        abort(404)
    docs = db.documents_for(doctor_id)
    my_jobs = {j["id"]: j for j in store.find("jobs", facility_id=g.user["id"])}
    apps = [dict(a, title=my_jobs[a["job_id"]]["title"]) for a in
            db.newest_first(store.find("applications", doctor_id=doctor_id)) if a["job_id"] in my_jobs]
    open_jobs = sorted([j for j in my_jobs.values() if j["status"] == "open"], key=lambda j: j["start_date"])
    invites = [db.invitation_full(i) for i in
               db.newest_first(store.find("invitations", facility_id=g.user["id"], doctor_id=doctor_id))]
    return render_template("facility/doctor.html", fac=fac, d=d, docs=docs, apps=apps, open_jobs=open_jobs,
                           invites=invites)


@bp.route("/doctors/<doctor_id>/invite", methods=["POST"])
@login_required("facility")
def invite(doctor_id):
    fac = get_facility(g.user["id"])
    if not fac["verified"] or not can_view_doctor(fac, doctor_id):
        abort(403)
    job_id = request.form.get("job_id") or None
    job = None
    if job_id:
        job = store.get("jobs", job_id)
        if not job or job["facility_id"] != g.user["id"] or job["status"] != "open":
            abort(400)
    message = (request.form.get("message") or "").strip()[:2000]
    if store.find("invitations", facility_id=g.user["id"], doctor_id=doctor_id, job_id=job_id, status="sent"):
        flash(_("You've already sent this doctor an invitation that's waiting for a reply."), "info")
        return redirect(url_for(".doctor", doctor_id=doctor_id))
    store.add("invitations", {"facility_id": g.user["id"], "doctor_id": doctor_id, "job_id": job_id,
                              "message": message})
    d = get_doctor(doctor_id)
    mail.send(d["email"], "%(facility)s invited you to a locum role", "doctor_invited", d["lang"],
              {"facility": fac["name"]}, doctor=d, facility=fac["name"], job=job, message=message)
    flash(_("Invitation sent to Dr %(name)s.", name=d["last_name"]), "success")
    return redirect(url_for(".doctor", doctor_id=doctor_id))
