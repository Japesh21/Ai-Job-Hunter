CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    company     TEXT,
    location    TEXT,
    city        TEXT,
    job_type    TEXT,
    description TEXT,
    url         TEXT,
    source      TEXT,
    salary_min  INTEGER,
    salary_max  INTEGER,
    posted_at   TEXT,
    scraped_at  TEXT NOT NULL,
    is_active   INTEGER DEFAULT 1
);
"""

CREATE_MATCHED_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS matched_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL UNIQUE REFERENCES jobs(id),
    score       REAL NOT NULL,
    matched_at  TEXT NOT NULL,
    notes       TEXT
);
"""

CREATE_APPLICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id        TEXT NOT NULL REFERENCES jobs(id),
    applied_date  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'applied',
    resume_used   TEXT,
    cover_letter  TEXT,
    notes         TEXT,
    updated_at    TEXT NOT NULL,
    CONSTRAINT chk_status CHECK (status IN ('applied','interview','rejected','offer','withdrawn'))
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);",
    "CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at);",
    "CREATE INDEX IF NOT EXISTS idx_matched_jobs_score ON matched_jobs(score DESC);",
    "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);",
]

ALL_TABLES = [CREATE_JOBS_TABLE, CREATE_MATCHED_JOBS_TABLE, CREATE_APPLICATIONS_TABLE]
