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
            "LOCAL_STORE_PATH": os.path.join(self.tmp, "store.json"),
            "FIREBASE_PROJECT_ID": "",
            "FIREBASE_STORAGE_BUCKET": "",
            "LEGACY_SQLITE_PATH": "",
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

    def rows(self, coll, **filters):
        with self.app.app_context():
            from locumdoc import store
            return sorted(store.find(coll, **filters), key=lambda r: r.get("created_at") or "")

    def user_id(self, email):
        return self.rows("users", email=email)[0]["id"]

    def signup_doctor(self, email="doc@x.test", ready=True):
        c = self.client()
        spec = "anaesthesia"
        r = self.post(c, "/join/doctor", {"first_name": "Amal", "last_name": "Nasser", "email": email,
                                          "password": "long-password-1", "specialty_id": spec,
                                          "grade": "consultant", "consent": "1", "visible": "1"})
        self.assertEqual(r.status_code, 302, r.data[:500])
        if ready:
            r = self.post(c, "/doctor/profile", {
                "title": "Dr", "first_name": "Amal", "last_name": "Nasser", "phone_country": "GB", "phone": "07911 123456", "nationality": "United Kingdom", "medical_school": "University of Leeds", "graduation_year": "2008",
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
        city = "qa-doha"
        r = self.post(c, "/join/facility", {"name": name, "facility_type": "hospital", "sector": "private",
                                            "city_id": city, "contact_name": "Hana", "phone_country": "QA", "phone": "4400 1234",
                                            "email": email, "password": "long-password-2", "consent": "1"})
        self.assertEqual(r.status_code, 302, r.data[:800])
        return c

    def admin(self):
        c = self.client()
        r = self.post(c, "/login", {"email": "admin@x.test", "password": "admin-pass-123"})
        self.assertEqual(r.status_code, 302)
        return c

    def post_job(self, c, title="Locum anaesthetist"):
        spec = "anaesthesia"
        city = "qa-doha"
        r = self.post(c, "/facility/jobs/new", {
            "title": title, "specialty_id": spec, "grade": "consultant", "city_id": city,
            "start_date": "2030-02-01", "end_date": "2030-05-01", "rate_amount": "70,000", "rate_period": "month",
            "accommodation": "1", "description": "Cover for leave."})
        self.assertEqual(r.status_code, 302, r.data[:800])
        return re.search(r"/facility/jobs/([A-Za-z0-9_-]+)$", r.headers["Location"]).group(1)


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
        self.assertEqual(len(self.rows("enquiries")), 1)
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
        fid = self.rows("facilities")[0]["id"]
        self.assertEqual(self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"}).status_code, 302)
        self.assertIn(b"Locum anaesthetist", self.client().get("/jobs").data)
        self.assertTrue(any("verified" in m["Subject"] for m in self.outbox()))

        # doctor applies
        r = self.post(doc, f"/doctor/jobs/{job_id}/apply", {"cover_note": "Free from Feb"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(self.rows("applications")), 1)
        subjects = [m["Subject"] for m in self.outbox()]
        self.assertIn("New applicant: Locum anaesthetist", subjects)
        # duplicate apply is ignored
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {})
        self.assertEqual(len(self.rows("applications")), 1)

        # facility sees applicant and CV
        page = fac.get(f"/facility/jobs/{job_id}").data
        self.assertIn(b"Amal", page)
        did = self.rows("doctors")[0]["id"]
        doc_file = self.rows("documents")[0]["id"]
        self.assertEqual(fac.get(f"/facility/doctors/{did}").status_code, 200)
        self.assertEqual(fac.get(f"/files/{doc_file}").data, PDF)

        # status change emails the doctor
        app_id = self.rows("applications")[0]["id"]
        self.post(fac, f"/facility/applications/{app_id}/status", {"status": "shortlisted"})
        self.assertEqual(self.rows("applications")[0]["status"], "shortlisted")
        self.assertTrue(any(m["Subject"].startswith("Update on your application") for m in self.outbox()))
        self.assertIn(b"Shortlisted", doc.get("/doctor/applications").data)

        # doctor withdraws
        self.post(doc, f"/doctor/applications/{app_id}/withdraw")
        self.assertEqual(self.rows("applications")[0]["status"], "withdrawn")

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
        fid = self.rows("facilities")[0]["id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {})
        self.assertEqual(len(self.rows("applications")), 0)
        self.assertIn(b"Before you apply", doc.get(f"/jobs/{job_id}").data)

    def test_directory_and_invitations(self):
        doc = self.signup_doctor()
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        adm = self.admin()
        fid = self.rows("facilities")[0]["id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.assertIn(b"Amal Nasser", fac.get("/facility/doctors?licence=any_progress&available=2030-03-01").data)
        self.assertNotIn(b"Amal Nasser", fac.get("/facility/doctors?licence=licensed").data)
        did = self.rows("doctors")[0]["id"]
        self.post(fac, f"/facility/doctors/{did}/invite", {"job_id": job_id, "message": "Join us"})
        inv = self.rows("invitations")[0]
        self.assertTrue(any("invited you" in m["Subject"] for m in self.outbox()))
        self.post(doc, f"/doctor/invitations/{inv['id']}", {"answer": "accepted"})
        self.assertEqual(self.rows("applications")[0]["status"], "shortlisted")

    def test_access_control(self):
        doc = self.signup_doctor()
        other = self.signup_doctor("other@x.test")
        fac = self.signup_facility()  # unverified
        did = self.user_id("doc@x.test")
        file_id = self.rows("documents", user_id=did)[0]["id"]
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
        fid = self.rows("facilities")[0]["id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.assertEqual(fac.get(f"/files/{file_id}").status_code, 200)
        with self.app.app_context():
            from locumdoc import store
            store.update("doctors", did, visible_to_facilities=0)
        self.assertEqual(fac.get(f"/files/{file_id}").status_code, 404)

    def test_documents_must_be_pdf(self):
        doc = self.signup_doctor(ready=False)
        docx = b"PK\x03\x04" + b"\x00" * 64
        jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 64
        for kind, data, name in (("cv", docx, "cv.docx"), ("license", docx, "licence.docx"),
                                 ("passport", jpg, "passport.jpg"), ("cv", docx, "renamed.pdf")):
            r = self.post(doc, "/doctor/documents", {"kind": kind, "file": (io.BytesIO(data), name)},
                          content_type="multipart/form-data", follow_redirects=True)
            self.assertTrue(b"must be PDFs" in r.data or b"look like a valid PDF" in r.data, name)
        self.assertEqual(len(self.rows("documents")), 0)
        self.post(doc, "/doctor/documents", {"kind": "license", "file": (io.BytesIO(PDF), "licence.pdf")},
                  content_type="multipart/form-data")
        self.assertEqual([d["kind"] for d in self.rows("documents")], ["license"])

    def test_upload_validation(self):
        doc = self.signup_doctor(ready=False)
        self.post(doc, "/doctor/documents", {"kind": "cv", "file": (io.BytesIO(b"MZ\x90evil"), "cv.pdf")},
                  content_type="multipart/form-data")
        self.post(doc, "/doctor/documents", {"kind": "cv", "file": (io.BytesIO(b"hello"), "cv.exe")},
                  content_type="multipart/form-data")
        self.assertEqual(len(self.rows("documents")), 0)

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
        self.assertEqual(len(self.rows("doctors")), 0)

    def test_country_toggle(self):
        adm = self.admin()
        self.post(adm, "/admin/countries", {"action": "toggle", "country_id": "AE"})
        self.assertIn(b"Dubai, United Arab Emirates", self.client().get("/join/facility").data)


if __name__ == "__main__":
    unittest.main()


class EnglishOnlyTests(Base):
    """Arabic was removed on 13 Oct 2026 (kept on the arabic-archive branch)."""
    ARABIC = re.compile("[\u0600-\u06ff]")

    def visible_arabic(self, html):
        return self.ARABIC.findall(html)

    def test_pages_are_english_even_for_arabic_browsers(self):
        c = self.client()
        c.set_cookie("lang", "ar")
        for url in ["/", "/jobs", "/for-facilities", "/countries/qatar", "/about", "/privacy", "/terms", "/contact",
                    "/join/doctor", "/cookies"]:
            html = c.get(url, headers={"Accept-Language": "ar-QA,ar;q=0.9"}).data.decode()
            self.assertIn('<html lang="en" dir="ltr"', html, url)
            self.assertEqual(self.visible_arabic(html), [], url)
            self.assertNotIn("/language/", html, url)

    def test_old_language_links_return_to_the_page(self):
        c = self.client()
        r = c.get("/language/ar?next=/jobs")
        self.assertTrue(r.headers["Location"].endswith("/jobs"))
        self.assertTrue(c.get("/language/ar?next=//evil.example").headers["Location"].endswith("/"))

    def test_emails_are_english(self):
        doc = self.signup_doctor()
        doc.set_cookie("lang", "ar")
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        self.post(self.admin(), f"/admin/facilities/{self.rows('facilities')[0]['id']}", {"action": "verify"})
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {})
        self.post(fac, f"/facility/applications/{self.rows('applications')[0]['id']}/status", {"status": "interview"})
        mail = [m for m in self.outbox() if m["To"] == "doc@x.test"][-1]
        self.assertTrue(mail["Subject"].startswith("Update on your application"))
        self.assertEqual(self.ARABIC.findall(mail.get_content()), [])


class GradeTests(Base):
    def test_academic_title_saved_shown_and_filtered(self):
        doc = self.signup_doctor()
        spec = "anaesthesia"
        r = self.post(doc, "/doctor/profile", {
            "title": "Prof", "first_name": "Amal", "last_name": "Nasser", "phone_country": "GB", "phone": "07911 123456", "nationality": "United Kingdom", "medical_school": "University of Leeds", "graduation_year": "2008",
            "current_country": "United Kingdom", "specialty_id": spec, "grade": "senior_consultant",
            "academic_rank": "associate_professor", "years_experience": "22", "qualifications": "MBBS, FRCA",
            "primary_license": "GMC", "qatar_license_status": "eligible", "exam_status": "exempt",
            "available_from": "2030-01-01", "visible_to_facilities": "1"})
        self.assertEqual(r.status_code, 302)
        row = self.rows("doctors")[0]
        self.assertEqual((row["grade"], row["academic_rank"]), ("senior_consultant", "associate_professor"))
        fac = self.signup_facility()
        adm = self.admin()
        fid = self.rows("facilities")[0]["id"]
        self.post(adm, f"/admin/facilities/{fid}", {"action": "verify"})
        self.assertIn(b"Associate professor", fac.get("/facility/doctors?academic=4").data)   # level 4 or above
        self.assertIn(b"Amal Nasser", fac.get("/facility/doctors?academic=any").data)
        self.assertNotIn(b"Amal Nasser", fac.get("/facility/doctors?academic=5").data)     # professor or above
        # An Egyptian "assistant professor" (أستاذ مساعد) sits at the Gulf associate-professor level
        base = {"title": "Dr", "first_name": "Amal", "last_name": "Nasser", "phone": "+20 100 123 4567", "nationality": "Egypt",
                "medical_school": "Cairo University (Kasr Al Ainy)", "graduation_year": "2005",
                "current_country": "Egypt", "specialty_id": spec, "grade": "consultant", "years_experience": "20",
                "qualifications": "MBBCh, MD", "primary_license": "Egyptian Medical Syndicate",
                "qatar_license_status": "eligible", "exam_status": "exempt", "available_from": "2030-01-01",
                "visible_to_facilities": "1"}
        self.post(doc, "/doctor/profile", dict(base, academic_rank="eg_assistant_professor"))
        self.assertIn(b"Amal Nasser", fac.get("/facility/doctors?academic=4").data)
        self.assertNotIn(b"Amal Nasser", fac.get("/facility/doctors?academic=5").data)
        did = self.rows("doctors")[0]["id"]
        page = fac.get(f"/facility/doctors/{did}").data
        self.assertIn(b"Assistant professor (Egypt)", page)
        self.assertIn(b"equivalent to associate professor", page)
        self.assertIn(b"Cairo University (Kasr Al Ainy)", page)
        # nationality must come from the country list; university is required
        r = self.post(doc, "/doctor/profile", dict(base, nationality="Egyptian", medical_school=""))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.rows("doctors")[0]["nationality"], "Egypt")
        # clearing it is allowed
        self.post(doc, "/doctor/profile", {
            "title": "Dr", "first_name": "Amal", "last_name": "Nasser", "phone_country": "GB", "phone": "07911 123456", "nationality": "United Kingdom", "medical_school": "University of Leeds", "graduation_year": "2008",
            "current_country": "United Kingdom", "specialty_id": spec, "grade": "consultant", "academic_rank": "",
            "years_experience": "22", "qualifications": "MBBS", "primary_license": "GMC",
            "qatar_license_status": "eligible", "exam_status": "exempt"})
        self.assertEqual(self.rows("doctors")[0]["academic_rank"], "")

    def test_phone_numbers_checked_per_country(self):
        doc = self.signup_doctor()
        base = {"title": "Dr", "first_name": "Amal", "last_name": "Nasser", "nationality": "United Kingdom",
                "medical_school": "University of Leeds", "current_country": "United Kingdom", "specialty_id": "anaesthesia",
                "grade": "consultant", "years_experience": "12", "qualifications": "MBBS", "primary_license": "GMC",
                "qatar_license_status": "eligible", "exam_status": "exempt"}
        stored = lambda: self.rows("doctors")[0]["phone"]
        # A Qatari number with the Qatar code is stored in international form
        self.assertEqual(self.post(doc, "/doctor/profile", dict(base, phone_country="QA", phone="5512 3456")).status_code, 302)
        self.assertEqual(stored(), "+97455123456")
        # Too short for Qatar, or nonsense: rejected with the country named, nothing saved
        for bad in ("1234", "999 999 999 999", "hello"):
            r = self.post(doc, "/doctor/profile", dict(base, phone_country="QA", phone=bad))
            self.assertEqual(r.status_code, 200, bad)
            self.assertIn(b"valid phone number for Qatar (+974)", r.data)
        self.assertEqual(stored(), "+97455123456")
        # A full international number overrides the dropdown
        self.post(doc, "/doctor/profile", dict(base, phone_country="QA", phone="+20 100 123 4567"))
        self.assertEqual(stored(), "+201001234567")
        # Shown formatted, and the form comes back with Egypt selected
        page = doc.get("/doctor/profile").data.decode()
        self.assertIn('<option value="EG" selected', page)
        self.assertIn('value="010 01234567"', page)
        fac = self.signup_facility()
        r = self.post(fac, "/facility/profile", {"name": "Test Hospital", "facility_type": "hospital", "sector": "private",
                                                 "city_id": "qa-doha", "contact_name": "Hana", "phone_country": "QA",
                                                 "phone": "12"})
        self.assertIn(b"valid phone number for Qatar", r.data)

    def test_import_from_old_sqlite_database(self):
        import sqlite3
        old = os.path.join(self.tmp, "old", "locumdoc.sqlite3")
        os.makedirs(os.path.join(self.tmp, "old", "uploads"))
        with open(os.path.join(self.tmp, "old", "uploads", "abc123.pdf"), "wb") as fh:
            fh.write(PDF)
        conn = sqlite3.connect(old)
        with open(os.path.join(os.path.dirname(__file__), "old_schema.sql")) as fh:
            conn.executescript(fh.read())
        conn.executescript("""
            INSERT INTO countries (id, code, name, slug, currency, active) VALUES (1, 'QA', 'Qatar', 'qatar', 'QAR', 1);
            INSERT INTO cities (id, country_id, name) VALUES (5, 1, 'Doha');
            INSERT INTO specialties (id, name, slug) VALUES (9, 'Radiology', 'radiology');
            INSERT INTO users (id, email, password_hash, role) VALUES (7, 'old@x.test', 'pbkdf2:x', 'doctor'),
                                                                     (8, 'fac@x.test', 'pbkdf2:y', 'facility');
            INSERT INTO doctors (user_id, first_name, last_name, specialty_id, nationality)
                VALUES (7, 'Mona', 'Fahmy', 9, 'Egyptian');
            INSERT INTO facilities (user_id, name, country_id, city_id, verified) VALUES (8, 'Old Clinic', 1, 5, 1);
            INSERT INTO documents (id, user_id, kind, original_name, storage_name, mime_type, size_bytes)
                VALUES (3, 7, 'cv', 'cv.pdf', 'abc123.pdf', 'application/pdf', 40);
            INSERT INTO jobs (id, facility_id, title, specialty_id, country_id, city_id, start_date, end_date)
                VALUES (4, 8, 'Radiologist', 9, 1, 5, '2030-01-01', '2030-03-01');
            INSERT INTO applications (id, job_id, doctor_id, status) VALUES (1, 4, 7, 'interview');
        """)
        conn.commit()
        conn.close()
        result = self.app.test_cli_runner().invoke(args=["import-sqlite", old])
        self.assertIn("2 accounts", result.output)
        d = self.rows("doctors")[0]
        self.assertEqual((d["id"], d["specialty_id"], d["nationality"]), ("7", "radiology", "Egypt"))
        self.assertEqual(self.rows("facilities")[0]["city_id"], "qa-doha")
        self.assertEqual(self.rows("applications")[0]["id"], "4_7")
        self.assertIn(b"Radiologist", self.client().get("/jobs/4").data)
        # running it again changes nothing
        self.app.test_cli_runner().invoke(args=["import-sqlite", old])
        self.assertEqual(len(self.rows("users", email="old@x.test")), 1)
        with self.app.app_context():
            from locumdoc import storage
            self.assertEqual(storage.read("abc123.pdf"), PDF)
