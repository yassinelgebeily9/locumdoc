import json
from datetime import date

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)

from .. import analytics, db, mail, store
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
        tests.append(lambda j: _matches(j["title"], q) or _matches(j["specialty"], q) or _matches(j["facility"], q))
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
            session["contact_sent"] = {"name": c["name"][:60], "email": c["email"]}
            analytics.track("generate_lead", form="contact")
            return redirect(url_for(".contact_thanks"))
    return render_template("public/contact.html", form=form)


@bp.route("/contact/thank-you")
def contact_thanks():
    """Shown once after the contact form; a direct visit without a message goes back to the form."""
    sent = session.pop("contact_sent", None)
    if not sent:
        return redirect(url_for(".contact"))
    return render_template("public/thanks.html", kind="contact", sent=sent)


@bp.route("/cookies", methods=["GET", "POST"])
def cookies():
    """Cookie settings. The banner posts here; without JavaScript it reloads the page you were on."""
    if request.method == "POST":
        choice = request.form.get("choice")
        if choice not in analytics.CHOICES:
            abort(400)
        back = request.form.get("next") or ""
        if not back.startswith("/") or back.startswith("//"):
            back = url_for(".home")
        resp = (Response(status=204) if request.headers.get("X-Requested-With") == "fetch" else redirect(back))
        resp.set_cookie(analytics.COOKIE, choice, max_age=analytics.MAX_AGE, samesite="Lax",
                        secure=current_app.config["SESSION_COOKIE_SECURE"])
        if request.headers.get("X-Requested-With") != "fetch":
            flash(_("Cookie settings saved."), "success")
        return resp
    return render_template("public/cookies.html", analytics_available=analytics.web_config() is not None)


def render_localized(name, **ctx):
    return render_template(f"public/{name}", **ctx)


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
    """The site is English-only now; old language-switch links simply return to the page."""
    target = request.args.get("next", "")
    if not target.startswith("/") or target.startswith("//"):
        target = url_for(".home")
    resp = redirect(target)
    resp.delete_cookie("lang")
    return resp


@bp.route("/robots.txt")
def robots():
    private = ["/doctor/", "/facility/", "/admin/", "/files/", "/account", "/reset-password/", "/language/",
               "/cookies", "/contact/thank-you"]
    body = "User-agent: *\n" + "".join(f"Disallow: {p}\n" for p in private)
    body += f"\nSitemap: {current_app.config['SITE_URL']}/sitemap.xml\n"
    return Response(body, mimetype="text/plain", headers={"Cache-Control": "public, max-age=3600"})


@bp.route("/favicon.ico")
def favicon():
    return send_from_directory(current_app.static_folder, "img/favicon.ico", mimetype="image/vnd.microsoft.icon",
                               max_age=7 * 24 * 3600)


@bp.route("/apple-touch-icon.png")
@bp.route("/apple-touch-icon-precomposed.png")
def apple_touch_icon():
    return send_from_directory(current_app.static_folder, "img/apple-touch-icon.png", max_age=7 * 24 * 3600)


@bp.route("/site.webmanifest")
def manifest():
    """Lets phones add LocumDoc to the home screen with the right name, colours and icons."""
    icon = lambda f: url_for("static", filename=f"img/{f}")  # noqa: E731
    data = {
        "name": "LocumDoc", "short_name": "LocumDoc", "lang": "en", "dir": "ltr",
        "description": _("Locum work for doctors of every specialty in the Gulf, starting with Qatar. One profile, one CV upload, verified hospitals and clinics."),
        "start_url": "/", "scope": "/", "display": "standalone", "background_color": "#f3f5f6", "theme_color": "#7a1631",
        "icons": [
            {"src": icon("icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": icon("icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": icon("icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
            {"src": icon("mark.svg"), "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/manifest+json")


@bp.route("/sitemap.xml")
def sitemap():
    base = current_app.config["SITE_URL"]
    jobs = public_jobs()
    newest = max((j["updated_at"] or "")[:10] for j in jobs) if jobs else None
    urls = [(url_for("public.home"), newest), (url_for("public.jobs"), newest)]
    urls += [(url_for(e), None) for e in ("public.for_facilities", "public.about", "public.contact", "auth.join",
                                          "auth.join_doctor", "auth.join_facility", "public.privacy", "public.terms")]
    urls += [(url_for("public.country", slug=c["slug"]), None) for c in db.countries()]
    urls += [(url_for("public.job", job_id=j["id"]), (j["updated_at"] or "")[:10] or None) for j in jobs]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"<url><loc>{base}{u}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>" for u, d in urls]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")
