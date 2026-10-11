-- LocumDoc database schema (SQLite; portable to PostgreSQL with minor type changes)

CREATE TABLE IF NOT EXISTS countries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,          -- ISO 3166 alpha-2, e.g. QA
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    currency        TEXT NOT NULL,                 -- ISO 4217, e.g. QAR
    licensing_body  TEXT NOT NULL DEFAULT '',
    active          INTEGER NOT NULL DEFAULT 0,    -- 1 = open for jobs and applications
    sort_order      INTEGER NOT NULL DEFAULT 100
);

CREATE TABLE IF NOT EXISTS cities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id  INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    UNIQUE (country_id, name)
);

CREATE TABLE IF NOT EXISTS specialties (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    slug    TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('doctor', 'facility', 'admin')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    lang            TEXT NOT NULL DEFAULT 'en',     -- preferred language for pages and emails
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at   TEXT
);

CREATE TABLE IF NOT EXISTS doctors (
    user_id                 INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    title                   TEXT NOT NULL DEFAULT 'Dr',
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    phone                   TEXT NOT NULL DEFAULT '',
    nationality             TEXT NOT NULL DEFAULT '',
    current_country         TEXT NOT NULL DEFAULT '',
    specialty_id            INTEGER REFERENCES specialties(id),
    subspecialty            TEXT NOT NULL DEFAULT '',
    grade                   TEXT NOT NULL DEFAULT '',
    years_experience        INTEGER,
    qualifications          TEXT NOT NULL DEFAULT '',   -- e.g. MBBS, MRCP, CCT
    primary_license         TEXT NOT NULL DEFAULT '',   -- e.g. GMC full registration
    qatar_license_status    TEXT NOT NULL DEFAULT 'none',
    has_psv                 INTEGER NOT NULL DEFAULT 0,  -- primary source verification report
    exam_status             TEXT NOT NULL DEFAULT 'unknown',
    good_standing           INTEGER NOT NULL DEFAULT 0,
    languages               TEXT NOT NULL DEFAULT '',
    available_from          TEXT,
    available_to            TEXT,
    min_weeks               INTEGER,
    preferred_countries     TEXT NOT NULL DEFAULT 'QA', -- comma-separated country codes
    bio                     TEXT NOT NULL DEFAULT '',
    visible_to_facilities   INTEGER NOT NULL DEFAULT 1,
    verified                INTEGER NOT NULL DEFAULT 0,
    admin_notes             TEXT NOT NULL DEFAULT '',
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS facilities (
    user_id         INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    facility_type   TEXT NOT NULL DEFAULT 'hospital',
    country_id      INTEGER REFERENCES countries(id),
    city_id         INTEGER REFERENCES cities(id),
    sector          TEXT NOT NULL DEFAULT 'private',
    website         TEXT NOT NULL DEFAULT '',
    contact_name    TEXT NOT NULL DEFAULT '',
    contact_role    TEXT NOT NULL DEFAULT '',
    phone           TEXT NOT NULL DEFAULT '',
    about           TEXT NOT NULL DEFAULT '',
    verified        INTEGER NOT NULL DEFAULT 0,
    admin_notes     TEXT NOT NULL DEFAULT '',
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL,       -- cv, license, passport, degree, psv, good_standing, other
    original_name   TEXT NOT NULL,
    storage_name    TEXT NOT NULL UNIQUE,
    mime_type       TEXT NOT NULL,
    size_bytes      INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id         INTEGER NOT NULL REFERENCES facilities(user_id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    specialty_id        INTEGER NOT NULL REFERENCES specialties(id),
    grade               TEXT NOT NULL DEFAULT '',
    country_id          INTEGER NOT NULL REFERENCES countries(id),
    city_id             INTEGER REFERENCES cities(id),
    start_date          TEXT NOT NULL,
    end_date            TEXT NOT NULL,
    rate_amount         INTEGER,
    rate_currency       TEXT NOT NULL DEFAULT 'QAR',
    rate_period         TEXT NOT NULL DEFAULT 'month',  -- day, week, month
    accommodation       INTEGER NOT NULL DEFAULT 0,
    flights             INTEGER NOT NULL DEFAULT 0,
    transport           INTEGER NOT NULL DEFAULT 0,
    licensing_support   INTEGER NOT NULL DEFAULT 0,
    description         TEXT NOT NULL DEFAULT '',
    requirements        TEXT NOT NULL DEFAULT '',
    status              TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'filled', 'closed')),
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(user_id) ON DELETE CASCADE,
    cover_note      TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'submitted',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (job_id, doctor_id)
);

CREATE TABLE IF NOT EXISTS invitations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_id     INTEGER NOT NULL REFERENCES facilities(user_id) ON DELETE CASCADE,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(user_id) ON DELETE CASCADE,
    job_id          INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    message         TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'sent',   -- sent, accepted, declined
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS enquiries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    organisation TEXT NOT NULL DEFAULT '',
    message     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, country_id, specialty_id);
CREATE INDEX IF NOT EXISTS idx_apps_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_apps_doctor ON applications(doctor_id);
CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_doctors_specialty ON doctors(specialty_id);
