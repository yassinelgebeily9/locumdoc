"""Sign in with Google (Firebase Authentication). Google's token check is replaced by a stand-in."""
from unittest import mock

from locumdoc import analytics, google_auth
from tests.test_app import Base

SNIPPET = '''const firebaseConfig = {
  apiKey: "AIza-test",
  authDomain: "locumdoc-test.firebaseapp.com",
  projectId: "locumdoc-test",
  storageBucket: "locumdoc-test.firebasestorage.app",
  messagingSenderId: "123",
  appId: "1:123:web:abc",
  measurementId: "G-TEST123",
};'''


def claims(email, name="Mona Fahmy", sub="google-uid-1"):
    return {"email": email, "email_verified": True, "name": name, "sub": sub,
            "iss": "https://securetoken.google.com/locumdoc-test", "firebase": {"sign_in_provider": "google.com"}}


class GoogleSigninTests(Base):
    def setUp(self):
        super().setUp()
        self.app.config["FIREBASE_WEB_CONFIG"] = SNIPPET

    def google(self, c, email, intent="login", **kw):
        with mock.patch.object(google_auth, "verify", return_value=claims(email, **kw)):
            return self.post(c, "/auth/google", {"id_token": "tok", "intent": intent})

    def test_config_pasted_as_firebase_shows_it(self):
        with self.app.app_context():
            cfg = analytics.parse_web_config(SNIPPET)
        self.assertEqual(cfg["authDomain"], "locumdoc-test.firebaseapp.com")
        self.assertEqual(cfg["measurementId"], "G-TEST123")
        r = self.client().get("/login")
        self.assertIn(b"Continue with Google", r.data)
        csp = r.headers["Content-Security-Policy"]
        self.assertIn("https://apis.google.com", csp)
        self.assertIn("frame-src https://locumdoc-test.firebaseapp.com", csp)
        self.assertIn("https://identitytoolkit.googleapis.com", csp)
        self.assertIn(b"Continue with Google", self.client().get("/join/doctor").data)

    def test_no_button_without_config(self):
        self.app.config["FIREBASE_WEB_CONFIG"] = ""
        r = self.client().get("/login")
        self.assertNotIn(b"Continue with Google", r.data)
        self.assertIn("frame-src 'none'", r.headers["Content-Security-Policy"])
        self.assertEqual(self.post(self.client(), "/auth/google", {"id_token": "x"}).status_code, 404)

    def test_existing_account_logs_in_and_links_google(self):
        self.signup_doctor()
        c = self.client()
        r = self.google(c, "doc@x.test")
        self.assertEqual(r.json["redirect"], "/doctor/")
        self.assertEqual(c.get("/doctor/").status_code, 200)
        user = self.rows("users", email="doc@x.test")[0]
        self.assertEqual((user["google_uid"], user["email_verified"]), ("google-uid-1", 1))

    def test_new_google_user_finishes_doctor_sign_up_without_password(self):
        c = self.client()
        r = self.google(c, "new@gmail.test", intent="doctor")
        self.assertEqual(r.json["redirect"], "/join/doctor")
        page = c.get("/join/doctor").data.decode()
        self.assertIn("Signing up with Google", page)
        self.assertIn("new@gmail.test", page)
        self.assertIn('value="Mona"', page)
        self.assertNotIn('name="password"', page)
        r = self.post(c, "/join/doctor", {"first_name": "Mona", "last_name": "Fahmy", "specialty_id": "radiology",
                                          "grade": "consultant", "consent": "1"})
        self.assertEqual(r.status_code, 302, r.data[:600])
        user = self.rows("users", email="new@gmail.test")[0]
        self.assertEqual((user["password_hash"], user["email_verified"]), ("", 1))
        self.assertEqual(c.get("/doctor/").status_code, 200)
        # A Google-only account can't be logged into with a password, and is told why
        r = self.post(self.client(), "/login", {"email": "new@gmail.test", "password": "anything-long"})
        self.assertIn(b"signs in with Google", r.data)
        # Account page offers to set a password (no current one needed), then it works
        self.assertIn(b"Set a password", c.get("/account").data)
        self.post(c, "/account", {"action": "password", "new_password": "a-new-password-1"})
        r = self.post(self.client(), "/login", {"email": "new@gmail.test", "password": "a-new-password-1"})
        self.assertEqual(r.status_code, 302)

    def test_new_google_user_as_facility(self):
        c = self.client()
        self.assertEqual(self.google(c, "hr@clinic.test", intent="facility", name="Hana Ali").json["redirect"],
                         "/join/facility")
        self.assertIn('value="Hana Ali"', c.get("/join/facility").data.decode())
        r = self.post(c, "/join/facility", {"name": "Clinic", "facility_type": "hospital", "sector": "private",
                                            "city_id": "qa-doha", "contact_name": "Hana Ali", "phone_country": "QA",
                                            "phone": "4400 1234", "consent": "1"})
        self.assertEqual(r.status_code, 302, r.data[:600])
        self.assertEqual(self.rows("facilities")[0]["contact_name"], "Hana Ali")

    def test_cancel_and_choose_page(self):
        c = self.client()
        self.assertEqual(self.google(c, "x@gmail.test").json["redirect"], "/join")
        self.assertIn(b"To finish signing up with Google", c.get("/join").data)
        c.get("/auth/google/cancel")
        self.assertIn(b'name="password"', c.get("/join/doctor").data)

    def test_rejected_tokens_and_suspended_accounts(self):
        c = self.client()
        with mock.patch.object(google_auth, "verify", side_effect=google_auth.InvalidToken("bad")):
            r = self.post(c, "/auth/google", {"id_token": "forged"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("didn't work", r.json["error"])
        self.signup_doctor()
        uid = self.user_id("doc@x.test")
        self.post(self.admin(), f"/admin/doctors/{uid}", {"action": "suspend"})
        self.assertEqual(self.google(self.client(), "doc@x.test").status_code, 403)
        # CSRF protection applies
        with mock.patch.object(google_auth, "verify", return_value=claims("doc@x.test")):
            self.assertEqual(self.client().post("/auth/google", data={"id_token": "t"}).status_code, 400)

    def test_google_only_account_deletes_with_email(self):
        c = self.client()
        self.google(c, "gone@gmail.test", intent="doctor")
        self.post(c, "/join/doctor", {"first_name": "A", "last_name": "B", "specialty_id": "radiology",
                                      "grade": "consultant", "consent": "1"})
        self.post(c, "/account/delete", {"confirm_password": "wrong@x.test"})
        self.assertEqual(len(self.rows("users", email="gone@gmail.test")), 1)
        self.post(c, "/account/delete", {"confirm_password": "gone@gmail.test"})
        self.assertEqual(len(self.rows("users", email="gone@gmail.test")), 0)


class TokenCheckTests(Base):
    def test_only_google_tokens_for_this_project_with_verified_email(self):
        good = claims("a@x.test")
        cases = [(dict(good), True),
                 (dict(good, iss="https://securetoken.google.com/other"), False),
                 (dict(good, firebase={"sign_in_provider": "password"}), False),
                 (dict(good, email_verified=False), False)]
        with self.app.app_context():
            for c, ok in cases:
                with mock.patch("google.oauth2.id_token.verify_firebase_token", return_value=c):
                    if ok:
                        self.assertEqual(google_auth.verify("t", "locumdoc-test")["email"], "a@x.test")
                    else:
                        with self.assertRaises(google_auth.InvalidToken):
                            google_auth.verify("t", "locumdoc-test")
            with mock.patch("google.oauth2.id_token.verify_firebase_token", side_effect=ValueError("expired")):
                with self.assertRaises(google_auth.InvalidToken):
                    google_auth.verify("t", "locumdoc-test")
