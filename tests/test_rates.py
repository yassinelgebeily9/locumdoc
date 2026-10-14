"""Rates are private unless the facility chooses to show them on a job."""
from tests.test_app import Base


class RateVisibilityTests(Base):
    def live_job(self):
        doc = self.signup_doctor()
        fac = self.signup_facility()
        job_id = self.post_job(fac)
        fid = self.rows("facilities")[0]["id"]
        self.post(self.admin(), f"/admin/facilities/{fid}", {"action": "verify"})
        return doc, fac, job_id

    def test_rate_hidden_by_default(self):
        doc, fac, job_id = self.live_job()
        self.assertEqual(self.rows("jobs")[0]["show_rate"], 0)
        for c in (self.client(), doc):
            for url in (f"/jobs/{job_id}", "/jobs", "/"):
                page = c.get(url).data
                self.assertIn(b"Locum anaesthetist", page, url)
                self.assertNotIn(b"70,000", page, url)
            self.assertIn(b"Rate on request", c.get(f"/jobs/{job_id}").data)
        self.post(doc, f"/doctor/jobs/{job_id}/apply", {"cover_note": "Free from Feb"})
        apps = doc.get("/doctor/applications").data
        self.assertNotIn(b"70,000", apps)
        self.assertIn(b"Rate on request", apps)
        # the facility that posted it still sees its own rate, with a note that doctors don't
        own = fac.get(f"/jobs/{job_id}").data
        self.assertIn(b"QAR 70,000", own)
        self.assertIn(b"Only you can see this rate", own)
        self.assertIn(b"QAR 70,000", self.admin().get(f"/jobs/{job_id}").data)

    def test_facility_can_choose_to_show_the_rate(self):
        doc, fac, job_id = self.live_job()
        form = fac.get(f"/facility/jobs/{job_id}/edit").data
        self.assertIn(b'name="show_rate"', form)
        self.assertNotIn(b'name="show_rate" value="1" aria-describedby="h-show_rate" checked', form)
        r = self.post(fac, f"/facility/jobs/{job_id}/edit", {
            "title": "Locum anaesthetist", "specialty_id": "anaesthesia", "grade": "consultant", "city_id": "qa-doha",
            "start_date": "2030-02-01", "end_date": "2030-05-01", "rate_amount": "70000", "rate_period": "month",
            "show_rate": "1", "description": "Cover for leave."})
        self.assertEqual(r.status_code, 302, r.data[:600])
        self.assertEqual(self.rows("jobs")[0]["show_rate"], 1)
        for c in (self.client(), doc):
            self.assertIn(b"QAR 70,000", c.get(f"/jobs/{job_id}").data)
            self.assertIn(b"QAR 70,000", c.get("/jobs").data)
        self.assertNotIn(b"Only you can see this rate", fac.get(f"/jobs/{job_id}").data)
