"""End-to-end tests for LocumDoc. Run with: python -m unittest discover tests"""
import io
import os
import re
import shutil
import tempfile
import unittest

from locumdoc import create_app

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class Base(unittest.TestCase):
    def setUp(self):
        from locumdoc import security
        security._attempts.clear()  # the rate limiter is per-process; reset it between tests
        self.tmp = tempfile.mkdtemp()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test",
            "DATABASE": os.path.join(self.tmp, "t.sqlite3"),
            "UPLOAD_DIR": os.path.join(self.tmp, "uploads"),
            "ADMIN_EMAIL": "admin@x.test",
            "ADMIN_PASSWORD": "admin-pass-123",
            "ADMIN_NOTIFY_EMAIL": "ops@x.test",
        })
        os.makedirs(self.app.config["UPLOAD_DIR"], exist_ok=True)
        # ensure_db ran before test config applied the admin creds, so run it again
        from locumdoc.db import ensure_db
        ensure_db(self.app)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers ---------------------------------------------------------------
    def client(self):
        return self.app.test_client()

    def token(self, c):
        c.get("/login")
        with c.session_transaction() as s:
            return s["csrf"]

    def post(self, c, url, data=None, **kw):
        data = dict(data or {})
        data["csrf_token"] = self.token(c) if "csrf_token" not in data else data["csrf_token"]
        return c.post(url, data=data, **kw)

    def outbox(self):
        return self.app.extensions.get("outbox", [])

    def db(self, sql, args=()):
        with self.app.app_context():
            from locumdoc.db import query
            return query(sql, args)

    def signup_doctor(self, email="doc@x.test", ready=True):
        c = self.client()
        spec = self.db("SELECT id FROM specialties WHERE name='Anaesthesia'")[0]["id"]
        r = self.post(c, "/join/doctor", {"first_name": "Amal", "last_name": "Nasser", "email": email,
                                          "password": "long-password-1", "specialty_id": spec,
                                          "grade": "consultant", "consent": "1", "visible": "1"})
        self.assertEqual(r.status_code, 302, r.data[:500])
        if ready:
            r = self.post(c, "/doctor/profile", {
                "title": "Dr", "first_name": "Amal", "last_name": "Nasser", "phone": "+44 1", "nationality": "British",
                "current_country": "United Kingdom", "specialty_id": spec, "grade": "consultant",
                "years_experience": "12", "qualifications": "MBBS, FRCA", "primary_license": "GMC",
                "qatar_license_status": "evaluating", "exam_status": "exempt", "available_from": "2030-01-01",
                "preferred_countries": ["QA", "AE"], "visible_to_facilities": "1"})
            self.assertEqual(r.status_code, 302)
            r = self.post(c, "/doctor/documents", {"kind": "cv", "file": (io.BytesIO(PDF), "my cv.pdf")},
                          content_type="multipart/form-data")
            self.assertEqual(r.status_code, 302)
        return c

    def signup_facility(self, email="hr@x.test", name="Test Hospital"):
        c = self.client()
        city = self.db("SELECT id FROM cities WHERE name='Doha'")[0]["id"]
        r = self.post(c, "/join/facility", {"name": name, "facility_type": "hospital", "sector": "private",
                                            "city_id": city, "contact_name": "Hana", "phone": "+974 1",
                                            "email": email, "password": "long-password-2", "consent": "1"})
        self.assertEqual(r.status_code, 302, r.data[:800])
        return c

    def admin(self):
        c = self.client()
        r = self.post(c, "/login", {"email": "admin@x.test", "password": "admin-pass-123"})
        self.assertEqual(r.status_code, 302)
        return c

    def post_job(self, c, title="Locum anaesthetist"):
        spec = self.db("SELECT id FROM specialties WHERE name='Anaesthesia'")[0]["id"]
        city = self.db("SELECT id FROM cities WHERE name='Doha'")[0]["id"]
        r = self.post(c, "/facility/jobs/new", {
            "title": title, "specialty_id": spec, "grade": "consultant", "city_id": city,
            "start_date": "2030-02-01", "end_date": "2030-05-01", "rate_amount": "70,000", "rate_period": "month",
            "accommodation": "1", "description": "Cover for leave."})
        self.assertEqual(r.status_code, 302, r.data[:800])
        return int(re.search(r"/facility/jobs/(\d+)", r.headers["Location"]).group(1))


class PublicTests(Base):
    def test_public_pages(self):
        c = self.client()
        for url in ["/", "/jobs", "/for-facilities", "/countries/qatar", "/countries/uae", "/about", "/contact",
                    "/privacy", "/terms", "/join", "/join/doctor", "/join/facility", "/login", "/forgot-password",
                    "/robots.txt", "/sitemap.xml"]:
            self.assertEqual(c.get(url).status_code, 200, url)
        self.assertEqual(c.get("/countries/narnia").status_code, 404)

    def test_security_headers_and_csrf(self):
        c = self.client()
        r = c.get("/")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        r = c.post("/login", data={"email": "admin@x.test", "password": "admin-pass-123"})
        self.assertEqual(r.status_code, 400)

    def test_contact_form(self):
        c = self.client()
        r = self.post(c, "/contact", {"name": "A", "email": "a@b.co", "message": "Hello"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.db("SELECT * FROM enquiries")), 1)
        self.assertTrue(any("enquiry" in m["Subject"] for m in self.outbox()))


class FlowTests(Base):
    def test_full_marketplace_flow(self):
        doc = self.signup_doctor()
        fac = self.signup_facility()
        job_id = self.post_job(fac)

        # unverified facility: job hidden from doctors and public
        self.assertEqual(self.client().get(f"/jobs/{job_id}").status_code, 404)
        self.assertNotIn(b"Locum anaesthetist", self.client().get("/jobs").data)
        self.assertIn(b"directory opens once", fac.get("/facility/doctors").data)

        # admin verifies
        adm = self.admin()
        fid = self.db("SELECT user_id FROM facilities")[0]["user_id"]
        self.assertEqual(self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"}).status_code, 302)
        self.assertIn(b"Locum anaesthetist", self.client().get("/jobs").data)
        self.assertTrue(any("verified" in m["Subject"] for m in self.outbox()))

        # doctor applies
        r = self.post(doc, f"/doctor/jobs/{job_id}/apply", {"cover_note": "Free from Feb"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.db("SELECT * FROM applications")), 1)
        subjects = [m["Subject"] for m in self.outbox()]
        self.assertIn("New applicant: Locum anaesthetist", subjects)
        # duplicate apply is ignored
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {})
        self.assertEqual(len(self.db("SELECT * FROM applications")), 1)

        # facility sees applicant and CV
        page = fac.get(f"/facility/jobs/{job_id}").data
        self.assertIn(b"Amal", page)
        did = self.db("SELECT user_id FROM doctors")[0]["user_id"]
        doc_file = self.db("SELECT id FROM documents")[0]["id"]
        self.assertEqual(fac.get(f"/facility/doctors/{did}").status_code, 200)
        self.assertEqual(fac.get(f"/files/{doc_file}").data, PDF)

        # status change emails the doctor
        app_id = self.db("SELECT id FROM applications")[0]["id"]
        self.post(fac, f"/facility/applications/{app_id}/status", {"status": "shortlisted"})
        self.assertEqual(self.db("SELECT status FROM applications")[0]["status"], "shortlisted")
        self.assertTrue(any(m["Subject"].startswith("Update on your application") for m in self.outbox()))
        self.assertIn(b"Shortlisted", doc.get("/doctor/applications").data)

        # doctor withdraws
        self.post(doc, f"/doctor/applications/{app_id}/withdraw")
        self.assertEqual(self.db("SELECT status FROM applications")[0]["status"], "withdrawn")

        # admin pages render
        for url in ["/admin/", "/admin/doctors", f"/admin/doctors/{did}", "/admin/facilities",
                    f"/admin/facilities/{fid}", "/admin/jobs", "/admin/applications", "/admin/countries",
                    "/admin/enquiries", "/admin/doctors?export=csv"]:
            self.assertEqual(adm.get(url).status_code, 200, url)

    def test_apply_requires_ready_profile(self):
        doc = self.signup_doctor(ready=False)
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        adm = self.admin()
        fid = self.db("SELECT user_id FROM facilities")[0]["user_id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {})
        self.assertEqual(len(self.db("SELECT * FROM applications")), 0)
        self.assertIn(b"Before you apply", doc.get(f"/jobs/{job_id}").data)

    def test_directory_and_invitations(self):
        doc = self.signup_doctor()
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        adm = self.admin()
        fid = self.db("SELECT user_id FROM facilities")[0]["user_id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.assertIn(b"Amal Nasser", fac.get("/facility/doctors?licence=any_progress&available=2030-03-01").data)
        self.assertNotIn(b"Amal Nasser", fac.get("/facility/doctors?licence=licensed").data)
        did = self.db("SELECT user_id FROM doctors")[0]["user_id"]
        self.post(fac, f"/facility/doctors/{did}/invite", {"job_id": job_id, "message": "Join us"})
        inv = self.db("SELECT * FROM invitations")[0]
        self.assertTrue(any("invited you" in m["Subject"] for m in self.outbox()))
        self.post(doc, f"/doctor/invitations/{inv['id']}", {"answer": "accepted"})
        self.assertEqual(self.db("SELECT status FROM applications")[0]["status"], "shortlisted")

    def test_access_control(self):
        doc = self.signup_doctor()
        other = self.signup_doctor("other@x.test")
        fac = self.signup_facility()  # unverified
        file_id = self.db("SELECT d.id FROM documents d JOIN users u ON u.id=d.user_id WHERE u.email='doc@x.test'")[0]["id"]
        did = self.db("SELECT id FROM users WHERE email='doc@x.test'")[0]["id"]
        self.assertEqual(other.get(f"/files/{file_id}").status_code, 404)
        self.assertEqual(fac.get(f"/files/{file_id}").status_code, 404)
        self.assertEqual(fac.get(f"/facility/doctors/{did}").status_code, 404)
        self.assertEqual(self.client().get(f"/files/{file_id}").status_code, 302)
        self.assertEqual(doc.get("/admin/").status_code, 403)
        self.assertEqual(doc.get("/facility/").status_code, 403)
        self.assertEqual(fac.get("/doctor/").status_code, 403)
        self.assertEqual(doc.get(f"/files/{file_id}").status_code, 200)
        # hidden doctors are not visible even to verified facilities
        adm = self.admin()
        fid = self.db("SELECT user_id FROM facilities")[0]["user_id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.assertEqual(fac.get(f"/files/{file_id}").status_code, 200)
        with self.app.app_context():
            from locumdoc.db import execute
            execute("UPDATE doctors SET visible_to_facilities = 0 WHERE user_id = ?", (did,))
        self.assertEqual(fac.get(f"/files/{file_id}").status_code, 404)

    def test_upload_validation(self):
        doc = self.signup_doctor(ready=False)
        self.post(doc, "/doctor/documents", {"kind": "cv", "file": (io.BytesIO(b"MZ\x90evil"), "cv.pdf")},
                  content_type="multipart/form-data")
        self.post(doc, "/doctor/documents", {"kind": "cv", "file": (io.BytesIO(b"hello"), "cv.exe")},
                  content_type="multipart/form-data")
        self.assertEqual(len(self.db("SELECT * FROM documents")), 0)

    def test_login_reset_and_delete(self):
        self.signup_doctor()
        c = self.client()
        r = self.post(c, "/login", {"email": "doc@x.test", "password": "wrong-password"})
        self.assertIn(b"don&#39;t match", r.data)
        self.post(c, "/forgot-password", {"email": "doc@x.test"})
        mail = [m for m in self.outbox() if "Reset" in m["Subject"]][-1]
        link = re.search(r"(/reset-password/\S+)", mail.get_content()).group(1)
        self.assertEqual(self.post(c, link, {"password": "brand-new-pass-1"}).status_code, 302)
        r = self.post(c, "/login", {"email": "doc@x.test", "password": "brand-new-pass-1"})
        self.assertEqual(r.status_code, 302)
        # old link can't be reused
        self.assertEqual(self.post(c, link, {"password": "another-pass-12"}).status_code, 302)
        r = self.post(self.client(), "/login", {"email": "doc@x.test", "password": "another-pass-12"})
        self.assertEqual(r.status_code, 200)
        # delete account removes files
        files_before = os.listdir(self.app.config["UPLOAD_DIR"])
        self.assertTrue(files_before)
        self.post(c, "/account/delete", {"confirm_password": "brand-new-pass-1"})
        self.assertEqual(os.listdir(self.app.config["UPLOAD_DIR"]), [])
        self.assertEqual(len(self.db("SELECT * FROM doctors")), 0)

    def test_country_toggle(self):
        adm = self.admin()
        ae = self.db("SELECT id FROM countries WHERE code='AE'")[0]["id"]
        self.post(adm, "/admin/countries", {"action": "toggle", "country_id": ae})
        self.assertIn(b"Dubai, United Arab Emirates", self.client().get("/join/facility").data)


if __name__ == "__main__":
    unittest.main()


class ArabicTests(Base):
    def test_language_switch_and_rtl(self):
        c = self.client()
        r = c.get("/language/ar?next=/jobs")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.headers["Location"].endswith("/jobs"))
        page = c.get("/jobs").data.decode()
        self.assertIn('lang="ar" dir="rtl"', page)
        self.assertIn("الوظائف المؤقتة", page)
        self.assertIn("English", page)  # switch back link
        c.get("/language/en")
        self.assertIn('lang="en" dir="ltr"', c.get("/").data.decode())
        # unsafe redirect targets fall back to home
        self.assertTrue(c.get("/language/ar?next=//evil.example").headers["Location"].endswith("/"))
        self.assertEqual(c.get("/language/fr").status_code, 404)

    def test_browser_language_detected(self):
        r = self.client().get("/", headers={"Accept-Language": "ar-QA,ar;q=0.9,en;q=0.5"})
        self.assertIn('dir="rtl"', r.data.decode())

    def test_arabic_signup_gets_arabic_email_and_messages(self):
        c = self.client()
        c.set_cookie("lang", "ar")
        spec = self.db("SELECT id FROM specialties WHERE name='Anaesthesia'")[0]["id"]
        r = self.post(c, "/join/doctor", {"first_name": "", "last_name": "N", "email": "bad",
                                          "password": "x", "specialty_id": spec, "grade": "consultant"})
        page = r.data.decode()
        self.assertIn("يُرجى إدخال اسمك الأول.", page)
        self.assertIn("أدخل بريدًا إلكترونيًا صحيحًا.", page)
        self.post(c, "/join/doctor", {"first_name": "Amal", "last_name": "N", "email": "amal@x.test",
                                      "password": "long-password-1", "specialty_id": spec,
                                      "grade": "consultant", "consent": "1"})
        self.assertEqual(self.db("SELECT lang FROM users WHERE email='amal@x.test'")[0]["lang"], "ar")
        welcome = [m for m in self.outbox() if m["To"] == "amal@x.test"][-1]
        self.assertEqual(welcome["Subject"], "أهلًا بك في LocumDoc")
        self.assertIn("أكمل ملفك المهني", welcome.get_content())
        admin_mail = [m for m in self.outbox() if m["To"] == "ops@x.test"][-1]
        self.assertEqual(admin_mail["Subject"], "New doctor sign-up")

    def test_status_email_in_doctors_language(self):
        doc = self.signup_doctor()
        doc.get("/language/ar")  # saves the preference on the account
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        adm = self.admin()
        fid = self.db("SELECT user_id FROM facilities")[0]["user_id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {})
        app_id = self.db("SELECT id FROM applications")[0]["id"]
        self.post(fac, f"/facility/applications/{app_id}/status", {"status": "interview"})
        mail = [m for m in self.outbox() if m["To"] == "doc@x.test"][-1]
        self.assertTrue(mail["Subject"].startswith("تحديث على طلبك"))
        self.assertIn("الحالة الجديدة: مقابلة", mail.get_content())
        # facility is English, so its applicant email is English
        fac_mail = [m for m in self.outbox() if m["To"] == "hr@x.test" and "applicant" in m["Subject"]][-1]
        self.assertTrue(fac_mail["Subject"].startswith("New applicant"))

    def test_arabic_pages_render(self):
        doc = self.signup_doctor()
        doc.set_cookie("lang", "ar")
        for url in ["/", "/jobs", "/for-facilities", "/countries/qatar", "/countries/uae", "/about", "/privacy",
                    "/terms", "/contact", "/doctor/", "/doctor/profile", "/doctor/documents", "/doctor/applications",
                    "/account"]:
            r = doc.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertIn('dir="rtl"', r.data.decode(), url)
        self.assertIn("إدارة الكوادر الصحية", doc.get("/countries/qatar").data.decode())

    def test_admin_stays_english(self):
        adm = self.admin()
        adm.set_cookie("lang", "ar")
        self.assertIn('dir="ltr"', adm.get("/admin/").data.decode())

    def test_arabic_specialty_search(self):
        fac = self.signup_facility()
        self.post_job(fac)
        adm = self.admin()
        fid = self.db("SELECT user_id FROM facilities")[0]["user_id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.assertIn(b"Locum anaesthetist", self.client().get("/jobs?q=تخدير").data)
