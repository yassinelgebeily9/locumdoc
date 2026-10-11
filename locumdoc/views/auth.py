from flask import (Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from .. import mail, refdata, storage
from ..i18n import _
from ..db import create_user, execute, get_db, query
from ..security import client_ip, login_required, login_user, rate_limited
from . import Form

bp = Blueprint("auth", __name__)

MIN_PASSWORD = 10


def _safe_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


def home_for(user):
    return url_for({"doctor": "doctor.dashboard", "facility": "facility.dashboard", "admin": "admin.dashboard"}[user["role"]])


def _check_password(form, name="password"):
    pw = form.data.get(name) or ""
    if len(pw) < MIN_PASSWORD:
        form.errors[name] = _("Use at least %(n)s characters.", n=MIN_PASSWORD)
    return pw


def _active_locations():
    countries = query("SELECT * FROM countries WHERE active = 1 ORDER BY sort_order")
    cities = query(
        "SELECT ci.id, ci.name, co.name AS country FROM cities ci JOIN countries co ON co.id = ci.country_id"
        " WHERE co.active = 1 ORDER BY co.sort_order, ci.name"
    )
    return countries, cities


@bp.route("/join")
def join():
    if g.user:
        return redirect(home_for(g.user))
    return render_template("auth/join.html")


@bp.route("/join/doctor", methods=["GET", "POST"])
def join_doctor():
    if g.user:
        return redirect(home_for(g.user))
    specialties = query("SELECT id, name FROM specialties ORDER BY name")
    form = Form()
    if request.method == "POST":
        if rate_limited("signup:" + client_ip(), limit=10, window=3600):
            flash(_("Too many sign-ups from this network. Try again in an hour."), "error")
            return redirect(url_for(".join_doctor"))
        form.text("first_name", required=True, max_len=80, label=_("your first name"))
        form.text("last_name", required=True, max_len=80, label=_("your last name"))
        email = form.email()
        pw = _check_password(form)
        form.choice("specialty_id", [(s["id"], s["name"]) for s in specialties], label=_("your specialty"))
        form.choice("grade", refdata.GRADES, label=_("your grade"))
        if not form.flag("consent"):
            form.errors["consent"] = _("Agree to the terms and privacy notice to create an account.")
        if email and query("SELECT 1 FROM users WHERE email = ?", (email,), one=True):
            form.errors["email"] = _("An account with this email already exists. Log in instead.")
        if form.ok:
            uid = create_user(email, pw, "doctor", g.lang)
            c = form.clean
            execute(
                "INSERT INTO doctors (user_id, first_name, last_name, specialty_id, grade, visible_to_facilities)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (uid, c["first_name"], c["last_name"], int(c["specialty_id"]), c["grade"],
                 1 if request.form.get("visible") else 0),
            )
            user = query("SELECT * FROM users WHERE id = ?", (uid,), one=True)
            login_user(user)
            mail.send(email, "Welcome to LocumDoc", "welcome_doctor", g.lang, first_name=c["first_name"])
            mail.notify_admin("New doctor sign-up", "admin_new_user", kind="doctor",
                              name=f"Dr {c['first_name']} {c['last_name']}", email=email)
            flash(_("Account created. Finish your profile and upload your CV so facilities can find you."), "success")
            return redirect(url_for("doctor.profile"))
    return render_template("auth/join_doctor.html", form=form, specialties=specialties)


@bp.route("/join/facility", methods=["GET", "POST"])
def join_facility():
    if g.user:
        return redirect(home_for(g.user))
    countries, cities = _active_locations()
    form = Form()
    if request.method == "POST":
        if rate_limited("signup:" + client_ip(), limit=10, window=3600):
            flash(_("Too many sign-ups from this network. Try again in an hour."), "error")
            return redirect(url_for(".join_facility"))
        form.text("name", required=True, max_len=160, label=_("the facility name"))
        form.choice("facility_type", refdata.FACILITY_TYPES, label=_("a facility type"))
        form.choice("sector", refdata.SECTORS, label=_("a sector"))
        form.choice("city_id", [(c["id"], c["name"]) for c in cities], label=_("a city"))
        form.text("contact_name", required=True, max_len=120, label=_("your name"))
        form.text("contact_role", max_len=120)
        form.text("phone", required=True, max_len=40, label=_("a phone number"))
        email = form.email()
        pw = _check_password(form)
        if not form.flag("consent"):
            form.errors["consent"] = _("Agree to the terms and privacy notice to create an account.")
        if email and query("SELECT 1 FROM users WHERE email = ?", (email,), one=True):
            form.errors["email"] = _("An account with this email already exists. Log in instead.")
        if form.ok:
            c = form.clean
            city = query("SELECT * FROM cities WHERE id = ?", (int(c["city_id"]),), one=True)
            uid = create_user(email, pw, "facility", g.lang)
            execute(
                "INSERT INTO facilities (user_id, name, facility_type, sector, country_id, city_id, contact_name,"
                " contact_role, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, c["name"], c["facility_type"], c["sector"], city["country_id"], city["id"],
                 c["contact_name"], c["contact_role"], c["phone"]),
            )
            login_user(query("SELECT * FROM users WHERE id = ?", (uid,), one=True))
            mail.send(email, "Your LocumDoc facility account", "welcome_facility", g.lang,
                      contact_name=c["contact_name"], facility=c["name"])
            mail.notify_admin("New facility to verify", "admin_new_user", kind="facility",
                              name=c["name"], email=email)
            flash(_("Account created. We verify every facility before its jobs go live, usually within one working day. You can draft jobs now."), "success")
            return redirect(url_for("facility.dashboard"))
    return render_template("auth/join_facility.html", form=form, cities=cities)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(home_for(g.user))
    form = Form()
    if request.method == "POST":
        email = form.email()
        pw = request.form.get("password", "")
        if rate_limited("login:" + client_ip()) or rate_limited("login:" + email, limit=6):
            flash(_("Too many attempts. Wait 10 minutes, or reset your password."), "error")
            return render_template("auth/login.html", form=form), 429
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user and user["is_active"] and check_password_hash(user["password_hash"], pw):
            login_user(user)
            execute("UPDATE users SET last_login_at = datetime('now') WHERE id = ?", (user["id"],))
            return redirect(_safe_next(request.args.get("next")) or home_for(user))
        form.errors["password"] = _("That email and password don't match an account.")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash(_("You're logged out."), "info")
    return redirect(url_for("public.home"))


# ------------------------------------------------------------- password reset

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot():
    form = Form()
    if request.method == "POST":
        email = form.email()
        if form.ok and not rate_limited("reset:" + client_ip(), limit=5, window=3600):
            user = query("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,), one=True)
            if user:
                token = _serializer().dumps({"uid": user["id"], "v": user["password_hash"][-12:]})
                mail.send(email, "Reset your LocumDoc password", "reset_password", user["lang"],
                          link=current_app.config["SITE_URL"] + url_for(".reset", token=token))
        if form.ok:
            flash(_("If an account exists for that email, a reset link is on its way. It works for one hour."), "info")
            return redirect(url_for(".login"))
    return render_template("auth/forgot.html", form=form)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset(token):
    try:
        data = _serializer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        flash(_("That reset link has expired or was already used. Request a new one."), "error")
        return redirect(url_for(".forgot"))
    user = query("SELECT * FROM users WHERE id = ?", (data["uid"],), one=True)
    if not user or user["password_hash"][-12:] != data["v"]:
        flash(_("That reset link has expired or was already used. Request a new one."), "error")
        return redirect(url_for(".forgot"))
    form = Form()
    if request.method == "POST":
        pw = _check_password(form)
        if form.ok:
            execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(pw), user["id"]))
            flash(_("Password updated. Log in with your new password."), "success")
            return redirect(url_for(".login"))
    return render_template("auth/reset.html", form=form)


# ------------------------------------------------------------------- account

@bp.route("/account", methods=["GET", "POST"])
@login_required()
def account():
    form = Form()
    if request.method == "POST" and request.form.get("action") == "password":
        if not check_password_hash(g.user["password_hash"], request.form.get("current_password", "")):
            form.errors["current_password"] = _("Your current password is incorrect.")
        pw = _check_password(form, "new_password")
        if form.ok:
            execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(pw), g.user["id"]))
            login_user(query("SELECT * FROM users WHERE id = ?", (g.user["id"],), one=True))
            flash(_("Password changed."), "success")
            return redirect(url_for(".account"))
    return render_template("auth/account.html", form=form)


@bp.route("/account/delete", methods=["POST"])
@login_required("doctor", "facility")
def delete_account():
    if not check_password_hash(g.user["password_hash"], request.form.get("confirm_password", "")):
        flash(_("Enter your password to delete your account."), "error")
        return redirect(url_for(".account"))
    for d in query("SELECT storage_name FROM documents WHERE user_id = ?", (g.user["id"],)):
        storage.delete(d["storage_name"])
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ?", (g.user["id"],))
    db.commit()
    session.clear()
    flash(_("Your account and all your files have been deleted."), "info")
    return redirect(url_for("public.home"))
