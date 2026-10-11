from datetime import date

from flask import (Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, url_for)

from .. import i18n, mail, refdata
from ..i18n import _
from ..db import execute, query
from ..security import client_ip, rate_limited
from . import Form, page_args

bp = Blueprint("public", __name__)

JOB_SELECT = """
    SELECT j.*, s.name AS specialty, ci.name AS city, co.name AS country, co.slug AS country_slug,
           f.name AS facility, f.facility_type, f.sector
    FROM jobs j
    JOIN specialties s ON s.id = j.specialty_id
    JOIN countries co ON co.id = j.country_id
    LEFT JOIN cities ci ON ci.id = j.city_id
    JOIN facilities f ON f.user_id = j.facility_id
"""
PUBLIC_WHERE = "j.status = 'open' AND f.verified = 1 AND co.active = 1 AND j.end_date >= date('now')"


def public_jobs(where="", args=(), order="j.start_date", limit=None, offset=0):
    sql = JOB_SELECT + " WHERE " + PUBLIC_WHERE + (" AND " + where if where else "") + " ORDER BY " + order
    if limit:
        sql += f" LIMIT {int(limit)} OFFSET {int(offset)}"
    return query(sql, args)


@bp.route("/")
def home():
    jobs = public_jobs(limit=6)
    stats = query(
        "SELECT (SELECT COUNT(*) FROM jobs j JOIN facilities f ON f.user_id=j.facility_id JOIN countries co"
        " ON co.id=j.country_id WHERE " + PUBLIC_WHERE + ") AS open_jobs,"
        " (SELECT COUNT(DISTINCT j.specialty_id) FROM jobs j JOIN facilities f ON f.user_id=j.facility_id"
        " JOIN countries co ON co.id=j.country_id WHERE " + PUBLIC_WHERE + ") AS specialties",
        one=True,
    )
    countries = query("SELECT * FROM countries ORDER BY sort_order")
    return render_template("public/home.html", jobs=jobs, stats=stats, countries=countries)


@bp.route("/jobs")
def jobs():
    where, args = [], []
    f = {k: request.args.get(k, "").strip() for k in ("q", "specialty", "city", "grade", "country")}
    if f["q"]:
        # Also match Arabic specialty names, e.g. "تخدير" finds Anaesthesia jobs.
        ar_ids = [r["id"] for r in query("SELECT id, name FROM specialties")
                  if f["q"] in i18n.AR.get(r["name"], "")]
        id_clause = (" OR s.id IN (" + ",".join("?" * len(ar_ids)) + ")") if ar_ids else ""
        where.append("(j.title LIKE ? OR s.name LIKE ? OR f.name LIKE ?" + id_clause + ")")
        args += [f"%{f['q']}%"] * 3 + ar_ids
    if f["specialty"]:
        where.append("s.slug = ?")
        args.append(f["specialty"])
    if f["city"]:
        where.append("ci.name = ?")
        args.append(f["city"])
    if f["grade"]:
        where.append("j.grade = ?")
        args.append(f["grade"])
    if f["country"]:
        where.append("co.slug = ?")
        args.append(f["country"])
    w = " AND ".join(where)
    page, per, offset = page_args(20)
    total = query("SELECT COUNT(*) AS n FROM (" + JOB_SELECT + " WHERE " + PUBLIC_WHERE
                  + (" AND " + w if w else "") + ")", args, one=True)["n"]
    rows = public_jobs(w, args, limit=per, offset=offset)
    specialties = query("SELECT name, slug FROM specialties ORDER BY name")
    cities = query("SELECT ci.name FROM cities ci JOIN countries co ON co.id = ci.country_id WHERE co.active = 1"
                   " ORDER BY ci.name")
    applied = set()
    if g.user and g.user["role"] == "doctor":
        applied = {r["job_id"] for r in query("SELECT job_id FROM applications WHERE doctor_id = ?", (g.user["id"],))}
    return render_template("public/jobs.html", jobs=rows, total=total, f=f, specialties=specialties,
                           cities=cities, page=page, per=per, applied=applied)


@bp.route("/jobs/<int:job_id>")
def job(job_id):
    row = query(JOB_SELECT + " WHERE j.id = ?", (job_id,), one=True)
    if not row:
        abort(404)
    is_public = row["status"] == "open" and row["end_date"] >= date.today().isoformat()
    owner = g.user and g.user["id"] == row["facility_id"]
    is_admin = g.user and g.user["role"] == "admin"
    fac = query("SELECT verified FROM facilities WHERE user_id = ?", (row["facility_id"],), one=True)
    if not (owner or is_admin) and not (is_public and fac["verified"]):
        abort(404)
    application = None
    readiness = None
    if g.user and g.user["role"] == "doctor":
        application = query("SELECT * FROM applications WHERE job_id = ? AND doctor_id = ?",
                            (job_id, g.user["id"]), one=True)
        from .doctor import profile_readiness
        readiness = profile_readiness(g.user["id"])
    similar = public_jobs("j.specialty_id = ? AND j.id != ?", (row["specialty_id"], job_id), limit=3)
    return render_template("public/job.html", job=row, application=application, readiness=readiness,
                           similar=similar, is_public=is_public)


@bp.route("/for-facilities")
def for_facilities():
    return render_template("public/for_facilities.html")


@bp.route("/countries/<slug>")
def country(slug):
    c = query("SELECT * FROM countries WHERE slug = ?", (slug,), one=True)
    if not c:
        abort(404)
    cities = query("SELECT name FROM cities WHERE country_id = ? ORDER BY name", (c["id"],))
    jobs = public_jobs("co.id = ?", (c["id"],), limit=4) if c["active"] else []
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
            execute("INSERT INTO enquiries (name, email, organisation, message) VALUES (?, ?, ?, ?)",
                    (c["name"], c["email"], c["organisation"], c["message"]))
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
        execute("UPDATE users SET lang = ? WHERE id = ?", (code, g.user["id"]))
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
    urls += [url_for("public.country", slug=c["slug"]) for c in query("SELECT slug FROM countries")]
    urls += [url_for("public.job", job_id=j["id"]) for j in public_jobs()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"<url><loc>{base}{u}</loc></url>" for u in urls]
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")
