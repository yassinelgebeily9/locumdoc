"""The launch checklist: metadata, icons, robots/sitemap, error and thank-you pages, cookie consent,
analytics, error summaries, sticky CTA and image alt text. Run with the rest: python -m unittest discover tests"""
import json
import re

from tests.test_app import Base

PUBLIC = ["/", "/jobs", "/for-facilities", "/countries/qatar", "/countries/uae", "/about", "/contact", "/privacy",
          "/terms", "/join", "/join/doctor", "/join/facility", "/login"]
WEB_CONFIG = json.dumps({"apiKey": "AIza-test", "authDomain": "x.firebaseapp.com", "projectId": "x",
                         "appId": "1:2:web:3", "measurementId": "G-TEST123"})


def meta(html, attr, name):
    m = re.search(rf'<meta {attr}="{re.escape(name)}" content="([^"]*)"', html)
    return m.group(1) if m else None


class MetadataTests(Base):
    def test_every_public_page_has_its_own_title_and_description(self):
        c = self.client()
        titles, descs = {}, {}
        for lang in ("en", "ar"):
            c.set_cookie("lang", lang)
            for url in PUBLIC:
                html = c.get(url).data.decode()
                title = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
                desc = meta(html, "name", "description")
                self.assertTrue(desc and 50 <= len(desc) <= 200, f"{lang} {url}: description length {len(desc or '')}")
                self.assertNotIn(title, titles.get(lang, {}).values(), f"{lang} {url}: duplicate title")
                self.assertNotIn(desc, descs.get(lang, {}).values(), f"{lang} {url}: duplicate description")
                titles.setdefault(lang, {})[url], descs.setdefault(lang, {})[url] = title, desc
                self.assertEqual(meta(html, "name", "robots"), "index, follow", url)
                self.assertIn('<link rel="canonical" href="http://localhost:5000' + url + '">', html)
                img = meta(html, "property", "og:image")
                self.assertTrue(img.startswith("http") and img.endswith(f"og-{lang}.png"), url)
                self.assertEqual(meta(html, "name", "twitter:card"), "summary_large_image")

    def test_site_url_always_has_a_scheme(self):
        from locumdoc import _site_url
        self.assertEqual(_site_url("locumdoc.me/"), "https://locumdoc.me")
        self.assertEqual(_site_url("http://localhost:5050"), "http://localhost:5050")
        self.assertEqual(_site_url(None), "http://localhost:5000")

    def test_private_and_one_off_pages_are_noindex(self):
        doc = self.client()
        self.assertIn('content="noindex, nofollow"', doc.get("/no-such-page").data.decode())
        self.assertIn('content="noindex, nofollow"', doc.get("/cookies").data.decode())
        self.assertIn('content="noindex, nofollow"', self.admin().get("/admin/").data.decode())

    def test_icons_manifest_and_share_images_are_served(self):
        c = self.client()
        r = c.get("/favicon.ico")
        self.assertEqual((r.status_code, r.mimetype), (200, "image/vnd.microsoft.icon"))
        self.assertEqual(c.get("/apple-touch-icon.png").status_code, 200)
        m = c.get("/site.webmanifest")
        self.assertEqual(m.mimetype, "application/manifest+json")
        data = json.loads(m.data)
        self.assertEqual(data["name"], "LocumDoc")
        self.assertTrue(any(i.get("purpose") == "maskable" for i in data["icons"]))
        for icon in data["icons"]:
            self.assertEqual(c.get(icon["src"]).status_code, 200, icon["src"])
        for f in ("og-en.png", "og-ar.png"):
            r = c.get("/static/img/" + f)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data[16:24], (1200).to_bytes(4, "big") + (630).to_bytes(4, "big"))  # PNG width/height
        html = c.get("/").data.decode()
        for rel in ('rel="icon"', 'rel="apple-touch-icon"', 'rel="manifest"'):
            self.assertIn(rel, html)

    def test_robots_and_sitemap(self):
        c = self.client()
        robots = c.get("/robots.txt").data.decode()
        for path in ("/doctor/", "/admin/", "/files/", "/account", "/contact/thank-you"):
            self.assertIn("Disallow: " + path, robots)
        self.assertIn("Sitemap: http://localhost:5000/sitemap.xml", robots)
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        self.post(self.admin(), f"/admin/facilities/{self.rows('facilities')[0]['id']}", {"action": "verify"})
        xml = c.get("/sitemap.xml").data.decode()
        for path in ("/privacy", "/terms", "/join/doctor", f"/jobs/{job_id}"):
            self.assertIn(f"<loc>http://localhost:5000{path}</loc>", xml)
        self.assertRegex(xml, r"<lastmod>\d{4}-\d\d-\d\d</lastmod>")

    def test_images_have_alt_text_and_icons_are_labelled_or_hidden(self):
        pages = [self.client().get(u).data.decode() for u in PUBLIC + ["/no-such-page"]]
        doc = self.signup_doctor()
        pages += [doc.get(u).data.decode() for u in ("/doctor/", "/doctor/profile", "/doctor/documents")]
        for html in pages:
            for img in re.findall(r"<img\b[^>]*>", html):
                self.assertRegex(img, r'\balt="', img)
            for svg in re.findall(r"<svg\b[^>]*>", html):
                ok = 'aria-hidden="true"' in svg or "aria-label=" in svg or 'role="img"' in svg
                if not ok:  # an svg inside a labelled link (the logo) is fine
                    i = html.index(svg)
                    ok = "aria-label=" in html[html.rfind("<a", 0, i):i]
                self.assertTrue(ok, svg)


class PageTests(Base):
    def test_404_page_helps_people_on(self):
        r = self.client().get("/jobs/does-not-exist")
        html = r.data.decode()
        self.assertEqual(r.status_code, 404)
        self.assertIn('role="search"', html)
        self.assertIn('href="/for-facilities"', html)

    def test_server_error_page(self):
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        @self.app.route("/boom")
        def boom():
            raise RuntimeError("test")
        r = self.client().get("/boom")
        self.assertEqual(r.status_code, 500)
        self.assertIn(b"Something went wrong on our side", r.data)
        self.assertNotIn(b"RuntimeError", r.data)

    def test_contact_thank_you_page(self):
        c = self.client()
        r = self.post(c, "/contact", {"name": "Hana", "email": "hana@x.test", "message": "Hello"})
        self.assertTrue(r.headers["Location"].endswith("/contact/thank-you"))
        page = c.get("/contact/thank-you").data.decode()
        self.assertIn("Thank you, Hana", page)
        self.assertIn("hana@x.test", page)
        # It's a one-off page: visiting it again goes back to the form
        self.assertTrue(c.get("/contact/thank-you").headers["Location"].endswith("/contact"))

    def test_application_thank_you_page(self):
        doc = self.signup_doctor()
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        self.post(self.admin(), f"/admin/facilities/{self.rows('facilities')[0]['id']}", {"action": "verify"})
        r = self.post(doc, f"/doctor/jobs/{job_id}/apply", {"cover_note": "Free from Feb"})
        self.assertIn("/sent", r.headers["Location"])
        page = doc.get(r.headers["Location"]).data.decode()
        self.assertIn("Application sent", page)
        self.assertIn("Locum anaesthetist", page)
        self.assertEqual(self.signup_doctor("other@x.test").get(r.headers["Location"]).status_code, 404)

    def test_legal_pages_cover_cookies_and_processors(self):
        c = self.client()
        privacy = c.get("/privacy").data.decode()
        for text in ('id="cookies"', "Google Analytics for Firebase", "Render", "Cookie settings"):
            self.assertIn(text, privacy)
        c.set_cookie("lang", "ar")
        self.assertIn("Google Analytics for Firebase", c.get("/privacy").data.decode())
        self.assertIn("13 Oct 2026", self.client().get("/terms").data.decode())


class ConsentAndAnalyticsTests(Base):
    def test_banner_until_a_choice_is_made(self):
        c = self.client()
        self.assertIn(b"data-cookie-banner", c.get("/").data)
        token = self.token(c)
        r = c.post("/cookies", data={"csrf_token": token, "choice": "analytics", "next": "/jobs"})
        self.assertTrue(r.headers["Location"].endswith("/jobs"))
        self.assertIn("ld_consent=analytics", r.headers["Set-Cookie"])
        self.assertNotIn(b"data-cookie-banner", c.get("/").data)
        # The banner's JavaScript path: no redirect, just the cookie
        r = c.post("/cookies", data={"csrf_token": token, "choice": "essential"}, headers={"X-Requested-With": "fetch"})
        self.assertEqual(r.status_code, 204)
        self.assertIn("ld_consent=essential", r.headers["Set-Cookie"])
        self.assertEqual(c.post("/cookies", data={"csrf_token": token, "choice": "everything"}).status_code, 400)
        self.assertTrue(c.post("/cookies", data={"csrf_token": token, "choice": "essential", "next": "//evil.example"})
                        .headers["Location"].endswith("/"))

    def test_no_analytics_without_firebase_config(self):
        r = self.client().get("/")
        self.assertNotIn(b"analytics.js", r.data)
        self.assertNotIn("googletagmanager", r.headers["Content-Security-Policy"])

    def test_analytics_loader_and_events_when_configured(self):
        self.app.config["FIREBASE_WEB_CONFIG"] = WEB_CONFIG
        c = self.client()
        r = c.get("/")
        html = r.data.decode()
        self.assertIn('id="ld-analytics-config"', html)
        self.assertIn('"measurementId": "G-TEST123"', html)
        self.assertIn("https://www.googletagmanager.com", r.headers["Content-Security-Policy"])
        self.assertIn("connect-src 'self' https://*.google-analytics.com", r.headers["Content-Security-Policy"])
        # Key moments are queued for the next page and sent only if the visitor allowed analytics (analytics.js)
        self.post(c, "/join/doctor", {"first_name": "A", "last_name": "B", "email": "a@x.test",
                                      "password": "long-password-1", "specialty_id": "anaesthesia",
                                      "grade": "consultant", "consent": "1"})
        events = re.search(r'id="ld-analytics-events">(.*?)</script>', c.get("/doctor/profile").data.decode()).group(1)
        self.assertEqual(json.loads(events)[0]["name"], "sign_up")
        # Never in the admin area
        self.assertNotIn(b"ld-analytics-config", self.admin().get("/admin/").data)

    def test_bad_config_turns_analytics_off(self):
        self.app.config["FIREBASE_WEB_CONFIG"] = '{"apiKey": "x"}'
        self.assertNotIn(b"analytics.js", self.client().get("/").data)


class FormStateTests(Base):
    def test_error_summary_links_to_each_field(self):
        c = self.client()
        r = self.post(c, "/join/doctor", {"first_name": "", "last_name": "N", "email": "bad", "password": "x",
                                          "specialty_id": "anaesthesia", "grade": "consultant"})
        html = r.data.decode()
        self.assertIn("data-error-summary", html)
        for field in ("first_name", "email", "password", "consent"):
            self.assertIn(f'href="#f-{field}"', html)
            self.assertIn(f'id="f-{field}"', html)

    def test_loading_labels_on_slow_actions(self):
        doc = self.signup_doctor(ready=False)
        self.assertIn(b'data-loading="Uploading', doc.get("/doctor/documents").data)
        self.assertIn(b"data-pdf-only", doc.get("/doctor/documents").data)
        self.assertIn(b'data-loading-text="Working', self.client().get("/").data)


class StickyCtaTests(Base):
    def test_sticky_cta_for_visitors_but_not_on_forms_or_when_logged_in(self):
        c = self.client()
        self.assertIn(b"data-sticky-cta", c.get("/").data)
        self.assertIn(b"Register your facility", c.get("/for-facilities").data.split(b"data-sticky-cta")[1][:300])
        for url in ("/join/doctor", "/login", "/contact"):
            self.assertNotIn(b"data-sticky-cta", c.get(url).data, url)
        self.assertNotIn(b"data-sticky-cta", self.signup_doctor().get("/jobs").data)

    def test_ctas_above_the_fold_markers(self):
        c = self.client()
        for url in ("/", "/for-facilities", "/countries/qatar", "/about", "/jobs"):
            self.assertIn(b"data-hero-cta", c.get(url).data, url)
