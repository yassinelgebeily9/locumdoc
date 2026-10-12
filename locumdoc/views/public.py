from datetime import date

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, url_for)

from .. import db, i18n, mail, store
from ..i18n import _
from ..db import public_jobs
from ..security import client_ip, rate_limited
from . import Form, page_args

bp = Blueprint("public", __name__)


@bp.route("/")
def home():
    jobs = public_jobs()
    stats = {"open_jobs": len(jobs), "specialties": len({j["specialty_id"] for j in jobs})}
    return render_template("public/home.html", jobs=jobs[:6], stats=stats, countries=db.countries())


def _matches(text, q):
    return q.casefold() in (text or "").casefold()


@bp.route("/jobs")
def jobs():
    f = {k: request.args.get(k, "").strip() for k in ("q", "specialty", "city", "grade", "country")}
    tests = []
    if f["q"]:
        q = f["q"]
        # Also match Arabic specialty names, e.g. "تخدير" finds Anaesthesia jobs.
        tests.append(lambda j: (_matches(j["title"], q) or _matches(j["specialty"], q) or _matches(j["facility"], q)
                                or q in i18n.AR.get(j["specialty"] or "", "")))
    if f["specialty"]:
        tests.append(lambda j: j["specialty_id"] == f["specialty"])
    if f["city"]:
        tests.append(lambda j: j["city"] == f["city"])
    if f["grade"]:
        tests.append(lambda j: j["grade"] == f["grade"])
    if f["country"]:
        tests.append(lambda j: j["country_slug"] == f["country"])
    matching = public_jobs(lambda j: all(t(j) for t in tests))
    page, per, offset = page_args(20)
    rows = matching[offset:offset + per]
    specialties = db.specialties()
    cities = sorted({c["name"] for c in db.cities(active_only=True)})
    applied = set()
    if g.user and g.user["role"] == "doctor":
        applied = {a["job_id"] for a in store.find("applications", doctor_id=g.user["id"])}
    return render_template("public/jobs.html", jobs=rows, total=len(matching), f=f, specialties=specialties,
                           cities=[{"name": n} for n in cities], page=page, per=per, applied=applied)


@bp.route("/jobs/<job_id>")
def job(job_id):
    row = db.get_job(job_id)
    if not row:
        abort(404)
    is_public = row["status"] == "open" and row["end_date"] >= date.today().isoformat()
    owner = g.user and g.user["id"] == row["facility_id"]
    is_admin = g.user and g.user["role"] == "admin"
    if not (owner or is_admin) and not (is_public and row["facility_verified"]):
        abort(404)
    application = None
    readiness = None
    if g.user and g.user["role"] == "doctor":
        application = store.first("applications", job_id=job_id, doctor_id=g.user["id"])
        from .doctor import profile_readiness
        readiness = profile_readiness(g.user["id"])
    similar = public_jobs(lambda j: j["specialty_id"] == row["specialty_id"] and j["id"] != job_id, limit=3)
    return render_template("public/job.html", job=row, application=application, readiness=readiness,
                           similar=similar, is_public=is_public)


@bp.route("/for-facilities")
def for_facilities():
    return render_template("public/for_facilities.html")


@bp.route("/countries/<slug>")
def country(slug):
    c = store.first("countries", slug=slug)
    if not c:
        abort(404)
    cities = sorted(store.find("cities", country_id=c["id"]), key=lambda x: x["name"])
    jobs = public_jobs(lambda j: j["country_id"] == c["id"], limit=4) if c["active"] else []
    if slug == "qatar":
        return render_localized("country_qatar.html", country=c, cities=cities, jobs=jobs)
    return render_template("public/country_soon.html", country=c, cities=cities, jobs=jobs)


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = Form()
    if request.method == "POST":
        form.text("name", required=True, max_len=120, label=_("your name"))
        form.email()
        form.text("organisation", max_len=160)
        form.text("message", required=True, max_len=4000, label=_("a message"))
        if request.form.get("website"):  # honeypot
            return redirect(url_for(".contact"))
        if form.ok and rate_limited("contact:" + client_ip(), limit=5, window=3600):
            form.errors["message"] = _("Too many messages from this network. Email us directly instead.")
        if form.ok:
            c = form.clean
            store.add("enquiries", {k: c[k] for k in ("name", "email", "organisation", "message")})
            mail.notify_admin("New enquiry from " + c["name"], "admin_enquiry", **c)
            flash(_("Message sent. We reply within one working day."), "success")
            return redirect(url_for(".contact"))
    return render_template("public/contact.html", form=form)


def render_localized(name, **ctx):
    """Long-form pages have a hand-written Arabic version in templates/public/ar/."""
    names = [f"public/ar/{name}", f"public/{name}"] if g.lang == "ar" else [f"public/{name}"]
    return render_template(names, **ctx)


@bp.route("/about")
def about():
    return render_localized("about.html")


@bp.route("/privacy")
def privacy():
    return render_localized("privacy.html")


@bp.route("/terms")
def terms():
    return render_localized("terms.html")


@bp.route("/language/<code>")
def set_language(code):
    """Switch the interface language and remember it (cookie, plus the account if logged in)."""
    if code not in i18n.LANGUAGES:
        abort(404)
    target = request.args.get("next", "")
    if not target.startswith("/") or target.startswith("//"):
        target = url_for(".home")
    resp = redirect(target)
    resp.set_cookie(i18n.COOKIE, code, max_age=365 * 24 * 3600, samesite="Lax", httponly=True,
                    secure=current_app.config["SESSION_COOKIE_SECURE"])
    if g.user:
        store.update("users", g.user["id"], lang=code)
    return resp


@bp.route("/robots.txt")
def robots():
    body = ("User-agent: *\nDisallow: /doctor/\nDisallow: /facility/\nDisallow: /admin/\nDisallow: /files/\n"
            f"Sitemap: {current_app.config['SITE_URL']}/sitemap.xml\n")
    return Response(body, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap():
    base = current_app.config["SITE_URL"]
    urls = [url_for(e) for e in ("public.home", "public.jobs", "public.for_facilities", "public.about",
                                 "public.contact", "auth.join")]
    urls += [url_for("public.country", slug=c["slug"]) for c in db.countries()]
    urls += [url_for("public.job", job_id=j["id"]) for j in public_jobs()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"<url><loc>{base}{u}</loc></url>" for u in urls]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")
