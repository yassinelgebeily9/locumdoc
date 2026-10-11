# LocumDoc — locumdoc.me

A two-sided locum marketplace for doctors and healthcare facilities in the Gulf, launching in Qatar.

- **Doctors** create a profile (specialty, grade, qualifications, licence, DHP licensing status, availability), upload their CV and credentials, apply to jobs, accept invitations and track every application.
- **Hospitals and clinics** register, get verified, post locum jobs, review applicants with CVs, move them through a pipeline (shortlisted → interview → offer → placed), and search a directory of doctors to invite.
- **Admins** verify facilities and doctors, see every job and application, export doctors to CSV, read contact-form messages, and open new countries.

Email notifications go out for sign-ups, new applications, status changes, invitations, verification and password resets.

## Run it locally

**On a Mac:** double-click `start-local.command` in Finder. It sets everything up on first run and opens the site at http://localhost:5050 with demo data (admin login: admin@test.local / admin-password-1).

**Manually** (Python 3.10+):

```bash
pip install -r requirements.txt
export SECRET_KEY=dev SEED_DEMO=1 ADMIN_EMAIL=admin@locumdoc.me ADMIN_PASSWORD=admin-password-1
flask --app wsgi run
```

Open http://localhost:5000. The database is created automatically in `instance/`.

Demo logins (only when `SEED_DEMO=1`), password `demo-password`:

| Role | Email |
|---|---|
| Facility | facility1@demo.locumdoc.me … facility3@ |
| Doctor | doctor1@demo.locumdoc.me … doctor4@ |
| Admin | whatever you set in `ADMIN_EMAIL` / `ADMIN_PASSWORD` |

Run the tests:

```bash
python -m unittest discover tests
```

## Languages (English and Arabic)

The whole doctor- and facility-facing site is available in English and Arabic, with a full right-to-left layout and the IBM Plex Sans Arabic font (self-hosted, SIL Open Font License). The admin panel stays in English.

- **Switching:** the header shows "العربية" / "English". The choice is remembered in a cookie and on the user's account. First-time visitors get Arabic automatically if their browser prefers it.
- **Emails** go out in each recipient's own language (`templates/email/ar/` holds the Arabic versions).
- **Long pages** (About, Privacy, Terms, the Qatar licensing guide) have hand-written Arabic versions in `templates/public/ar/`. The Arabic privacy notice and terms say the English text prevails; have them reviewed along with the English ones.
- **Short strings** are wrapped in `_("...")` in templates and Python, and translated in `locumdoc/translations/ar.py`. `tests/test_i18n.py` fails if any marked string is missing an Arabic translation, so new text can't slip through untranslated.
- **What stays in the original language:** anything users type (job titles, descriptions, names, notes) is shown as entered.

To add a third language later, add it to `LANGUAGES` in `locumdoc/i18n.py`, create `translations/<code>.py` and register it in `CATALOGS`.

## Put it live on locumdoc.me

The app is one Docker container plus a persistent disk (for the SQLite database and uploaded files). Two easy routes:

### Option A — Render (simplest, managed HTTPS)

1. Push this folder to a private GitHub repository.
2. On render.com: **New → Blueprint**, pick the repo. `render.yaml` creates the web service and a 5 GB disk.
3. Fill in the variables it asks for: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NOTIFY_EMAIL`, and the `SMTP_*` settings (see Email below).
4. In the service's **Settings → Custom domains**, add `locumdoc.me` and `www.locumdoc.me`.
5. At your domain registrar, create the DNS records Render shows you (typically an `A` record for `locumdoc.me` and a `CNAME` for `www`). HTTPS is issued automatically once DNS resolves.

### Option B — Any VPS with Docker (e.g. Hetzner, DigitalOcean)

```bash
docker build -t locumdoc .
docker run -d --name locumdoc --restart unless-stopped \
  -p 127.0.0.1:8000:8000 -v /srv/locumdoc:/data --env-file .env locumdoc
```

Put a reverse proxy with automatic HTTPS in front, for example Caddy with a two-line `Caddyfile`:

```
locumdoc.me, www.locumdoc.me {
    reverse_proxy 127.0.0.1:8000
}
```

Point the domain's `A` record at the server's IP.

### Email

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` from any transactional email provider (Postmark, Brevo, Amazon SES, or a Google Workspace / Zoho mailbox on hello@locumdoc.me). Add the SPF and DKIM DNS records your provider gives you so emails don't land in spam. Without SMTP settings the site still works and emails are written to the server log.

## Before launch

- [ ] Set a long random `SECRET_KEY` and `SECURE_COOKIES=1`.
- [ ] Keep `SEED_DEMO=0` (or unset) in production.
- [ ] Have a lawyer review `templates/public/privacy.html` and `terms.html`. They're written as a solid starting point covering GDPR and Qatar's PDPPL, but they aren't legal advice, and you'll need to add your company's legal name and address.
- [ ] Turn on daily backups of the disk (Render: disk snapshots; VPS: back up `/srv/locumdoc`, which holds `locumdoc.sqlite3` and `uploads/`).
- [ ] Check the Qatar licensing guide (`templates/public/country_qatar.html`) against DHP's current rules.
- [ ] Send yourself a test of each email: sign up as a doctor and a facility, apply, change a status, reset a password.

## Opening another country

In the admin panel go to **Countries**, add cities if needed, and click **Open**. Facilities in that country can then register and post jobs, and doctors who ticked that country as a preference already show up in searches. To add a dedicated guide page like Qatar's, create `templates/public/country_<slug>.html` and add the slug to the `country` view in `views/public.py`.

## How it's built

- Flask (Python), server-rendered HTML, no JavaScript framework. Pages work without JavaScript.
- SQLite with WAL mode: comfortably handles thousands of users on one server. To move to PostgreSQL later, swap `db.py`'s connection for `psycopg` and adjust the few SQLite-specific functions (`datetime('now')`, `INSERT OR IGNORE`, `GROUP_CONCAT`).
- Security: hashed passwords, CSRF tokens on every form, strict Content-Security-Policy, rate-limited login/sign-up/reset, private uploads stored under random names and served only to authorised users, file-type checks by content, session invalidated on password change.
- Fonts are self-hosted (TeX Gyre Adventor, Inter and IBM Plex Sans Arabic), so no visitor data goes to Google Fonts.

```
locumdoc/
  __init__.py       app factory, config, security headers, template filters
  db.py             database helpers, CLI commands, demo data
  schema.sql        tables
  refdata.py        countries, cities, specialties, option lists
  security.py       sessions, CSRF, role checks, rate limiting
  storage.py        private file uploads
  mail.py           email sending (in each recipient's language)
  i18n.py           language detection, translation, Arabic dates and numbers
  translations/     Arabic catalogue
  views/            public, auth, doctor, facility, admin, files
  templates/        HTML pages and email texts
  static/           CSS, fonts, logo, small JS
tests/test_app.py   end-to-end tests
```

Useful commands:

```bash
flask --app wsgi create-admin someone@locumdoc.me   # add another admin
flask --app wsgi seed-demo                           # add demo data
```
