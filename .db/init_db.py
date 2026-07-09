"""
init_db.py
-----------
Database initialization module for the Gov Job Portal ecosystem.

Design rules enforced here:
- Rule 1 (Idempotency): jobs.content_hash and alerts_sent(user_id, job_id)
  carry UNIQUE constraints so re-running scrapers/alert jobs never
  produces duplicate rows.
- Rule 2 (Robust Error Handling): every DDL statement runs through
  _execute_safely() so a partial failure during schema creation logs
  clearly instead of crashing the whole init process.
- WAL mode enabled for better read/write concurrency across parallel
  scraper processes (district court + nagar nigam + national scrapers
  running together).

Usage:
    from db.init_db import init_db
    init_db("gov_jobs.db")
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("init_db")


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Opens a SQLite connection with production-sensible PRAGMAs set.
    WAL mode allows concurrent readers while a writer (scraper) is active.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")   # cascades won't fire without this
    conn.execute("PRAGMA synchronous = NORMAL;")  # safe + fast under WAL
    return conn


def _execute_safely(conn: sqlite3.Connection, label: str, sql: str) -> None:
    """
    Wraps each DDL execution in try/except so one bad statement doesn't
    kill the whole init run (Rule 2). Logs failure and continues.
    """
    try:
        conn.execute(sql)
        logger.info("OK      : %s", label)
    except sqlite3.Error as e:
        logger.error("FAILED  : %s -> %s", label, e)


# ---------------------------------------------------------------------------
# Table group: Organizations & Jobs (core entities)
# ---------------------------------------------------------------------------

def create_organizations_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS organizations (
        org_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        org_type        TEXT NOT NULL CHECK (
                            org_type IN (
                                'central', 'state_psc', 'district_court',
                                'municipal', 'anganwadi', 'psu',
                                'defense', 'other'
                            )
                        ),
        state           TEXT,               -- NULL for central-level orgs
        tier            TEXT NOT NULL CHECK (
                            tier IN ('national', 'state', 'micro_niche')
                        ),
        official_website TEXT,
        created_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """
    _execute_safely(conn, "organizations", sql)
    _execute_safely(
        conn, "idx_organizations_tier",
        "CREATE INDEX IF NOT EXISTS idx_organizations_tier ON organizations(tier);"
    )
    _execute_safely(
        conn, "idx_organizations_name",
        "CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(name);"
    )


def create_jobs_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id          INTEGER NOT NULL,
        title           TEXT NOT NULL,
        slug            TEXT NOT NULL UNIQUE,
        post_category   TEXT,               -- e.g. '10th_pass','graduate','defense'
        status          TEXT NOT NULL DEFAULT 'upcoming' CHECK (
                            status IN ('upcoming', 'active', 'closed', 'result_declared')
                        ),
        source_url      TEXT,
        content_hash    TEXT NOT NULL UNIQUE,   -- idempotency guard (Rule 1)
        is_verified     INTEGER NOT NULL DEFAULT 0,  -- 0/1 manual QA flag
        first_scraped_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "jobs", sql)

    # Prefix-search friendly indexes (title, and joins on org_id/status)
    _execute_safely(
        conn, "idx_jobs_title",
        "CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);"
    )
    _execute_safely(
        conn, "idx_jobs_status",
        "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);"
    )
    _execute_safely(
        conn, "idx_jobs_org_id",
        "CREATE INDEX IF NOT EXISTS idx_jobs_org_id ON jobs(org_id);"
    )
    _execute_safely(
        conn, "idx_jobs_post_category",
        "CREATE INDEX IF NOT EXISTS idx_jobs_post_category ON jobs(post_category);"
    )


# ---------------------------------------------------------------------------
# Table group: Job metadata (dates, fees, age) - EAV-style child tables
# ---------------------------------------------------------------------------

def create_important_dates_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS important_dates (
        date_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id      INTEGER NOT NULL,
        event_type  TEXT NOT NULL CHECK (
                        event_type IN (
                            'notification', 'application_start', 'application_end',
                            'correction_window', 'fee_last_date', 'exam_date',
                            'admit_card_release', 'result_date', 'interview_date'
                        )
                    ),
        event_date  TEXT,                 -- nullable: tentative dates allowed
        is_tentative INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "important_dates", sql)
    _execute_safely(
        conn, "idx_dates_job_id",
        "CREATE INDEX IF NOT EXISTS idx_dates_job_id ON important_dates(job_id);"
    )


def create_application_fees_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS application_fees (
        fee_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id      INTEGER NOT NULL,
        category    TEXT NOT NULL,   -- general, obc, sc, st, ews, pwd, female, ex_servicemen
        amount      REAL NOT NULL,
        payment_mode TEXT,           -- online / offline / challan
        notes       TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "application_fees", sql)
    _execute_safely(
        conn, "idx_fees_job_id",
        "CREATE INDEX IF NOT EXISTS idx_fees_job_id ON application_fees(job_id);"
    )


def create_age_limits_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS age_limits (
        age_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id          INTEGER NOT NULL,
        category        TEXT NOT NULL,
        min_age         INTEGER,
        max_age         INTEGER,
        as_on_date      TEXT,
        relaxation_years REAL,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "age_limits", sql)
    _execute_safely(
        conn, "idx_age_job_id",
        "CREATE INDEX IF NOT EXISTS idx_age_job_id ON age_limits(job_id);"
    )


# ---------------------------------------------------------------------------
# Table group: Posts & Qualifications (post-level, NOT job-level)
# ---------------------------------------------------------------------------

def create_posts_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS posts (
        post_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id        INTEGER NOT NULL,
        post_name     TEXT NOT NULL,
        post_code     TEXT,
        total_vacancy INTEGER,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "posts", sql)
    _execute_safely(
        conn, "idx_posts_job_id",
        "CREATE INDEX IF NOT EXISTS idx_posts_job_id ON posts(job_id);"
    )


def create_post_vacancy_breakdown_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS post_vacancy_breakdown (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id         INTEGER NOT NULL,
        category        TEXT NOT NULL,
        vacancy_count   INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "post_vacancy_breakdown", sql)
    _execute_safely(
        conn, "idx_vacancy_post_id",
        "CREATE INDEX IF NOT EXISTS idx_vacancy_post_id ON post_vacancy_breakdown(post_id);"
    )


def create_qualifications_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS qualifications (
        qual_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id                 INTEGER NOT NULL,
        min_qualification       TEXT NOT NULL,   -- 10th, 12th, diploma, graduate, pg
        stream                  TEXT,            -- e.g. 'B.Tech CS/IT'
        additional_requirement  TEXT,            -- typing speed, experience, etc.
        FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "qualifications", sql)
    _execute_safely(
        conn, "idx_qual_post_id",
        "CREATE INDEX IF NOT EXISTS idx_qual_post_id ON qualifications(post_id);"
    )
    # Enables prefix search on qualification as agreed (relational indexing only)
    _execute_safely(
        conn, "idx_qual_min_qualification",
        "CREATE INDEX IF NOT EXISTS idx_qual_min_qualification ON qualifications(min_qualification);"
    )


# ---------------------------------------------------------------------------
# Table group: Links & Document specs
# ---------------------------------------------------------------------------

def create_useful_links_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS useful_links (
        link_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id          INTEGER NOT NULL,
        link_type       TEXT NOT NULL CHECK (
                            link_type IN (
                                'apply_online', 'notification_pdf', 'official_site',
                                'admit_card', 'result', 'answer_key', 'syllabus'
                            )
                        ),
        url             TEXT NOT NULL,
        is_active       INTEGER NOT NULL DEFAULT 1,
        last_checked_at TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "useful_links", sql)
    _execute_safely(
        conn, "idx_links_job_id",
        "CREATE INDEX IF NOT EXISTS idx_links_job_id ON useful_links(job_id);"
    )


def create_document_specs_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS document_specs (
        spec_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id      INTEGER,            -- NULL => generic/default spec
        doc_type    TEXT NOT NULL CHECK (doc_type IN ('photo', 'signature', 'thumb')),
        min_kb      INTEGER,
        max_kb      INTEGER,
        width_px    INTEGER,
        height_px   INTEGER,
        format      TEXT,               -- jpg/png
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "document_specs", sql)


# ---------------------------------------------------------------------------
# Table group: Prep ecosystem (static PYQ papers only, per current scope)
# ---------------------------------------------------------------------------

def create_exams_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS exams (
        exam_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id      INTEGER NOT NULL,
        exam_name   TEXT NOT NULL,
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "exams", sql)


def create_previous_year_papers_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS previous_year_papers (
        paper_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id         INTEGER NOT NULL,
        year            INTEGER NOT NULL,
        shift           TEXT,
        pdf_url         TEXT NOT NULL,
        has_solution    INTEGER NOT NULL DEFAULT 0,
        solution_url    TEXT,
        FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "previous_year_papers", sql)
    _execute_safely(
        conn, "idx_papers_exam_id",
        "CREATE INDEX IF NOT EXISTS idx_papers_exam_id ON previous_year_papers(exam_id);"
    )


def create_cutoffs_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS cutoffs (
        cutoff_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id         INTEGER NOT NULL,
        year            INTEGER NOT NULL,
        category        TEXT NOT NULL,
        post            TEXT,
        cutoff_marks    REAL,
        FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "cutoffs", sql)
    _execute_safely(
        conn, "idx_cutoffs_exam_id",
        "CREATE INDEX IF NOT EXISTS idx_cutoffs_exam_id ON cutoffs(exam_id);"
    )


# ---------------------------------------------------------------------------
# Table group: Users & AI Alerts
# ---------------------------------------------------------------------------

def create_user_profiles_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        qualification       TEXT,
        dob                 TEXT,
        category            TEXT,
        preferred_sectors   TEXT,   -- JSON array stored as text, e.g. '["defense","banking"]'
        preferred_states    TEXT,   -- JSON array stored as text
        alert_channel       TEXT CHECK (alert_channel IN ('email', 'push', 'whatsapp')),
        created_at          TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """
    _execute_safely(conn, "user_profiles", sql)
    _execute_safely(
        conn, "idx_user_qualification",
        "CREATE INDEX IF NOT EXISTS idx_user_qualification ON user_profiles(qualification);"
    )


def create_alerts_sent_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS alerts_sent (
        alert_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        job_id      INTEGER NOT NULL,
        sent_at     TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (user_id, job_id),   -- idempotency: never alert same user for same job twice
        FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
    );
    """
    _execute_safely(conn, "alerts_sent", sql)


# ---------------------------------------------------------------------------
# Table group: Operational logging (Rule 2 evidence trail)
# ---------------------------------------------------------------------------

def create_scrape_logs_table(conn: sqlite3.Connection) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS scrape_logs (
        log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id          INTEGER,
        url             TEXT,
        status          TEXT NOT NULL CHECK (
                            status IN ('success', 'failed', 'skipped_duplicate')
                        ),
        error_message   TEXT,
        attempted_at    TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (org_id) REFERENCES organizations(org_id) ON DELETE SET NULL
    );
    """
    _execute_safely(conn, "scrape_logs", sql)
    _execute_safely(
        conn, "idx_scrape_logs_org_id",
        "CREATE INDEX IF NOT EXISTS idx_scrape_logs_org_id ON scrape_logs(org_id);"
    )
    _execute_safely(
        conn, "idx_scrape_logs_status",
        "CREATE INDEX IF NOT EXISTS idx_scrape_logs_status ON scrape_logs(status);"
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def init_db(db_path: str = "gov_jobs.db") -> None:
    """
    Single entry point. Creates the DB file (if absent) and all tables/indexes.
    Safe to call repeatedly — every statement uses IF NOT EXISTS.
    """
    db_file = Path(db_path)
    logger.info("Initializing database at: %s", db_file.resolve())

    conn = get_connection(db_path)
    try:
        # Order matters only for readability here — FK constraints are
        # declared but not enforced at CREATE time in SQLite, so child
        # tables can technically be created before parents. We still
        # go parent -> child for clarity and future maintainability.
        create_organizations_table(conn)
        create_jobs_table(conn)

        create_important_dates_table(conn)
        create_application_fees_table(conn)
        create_age_limits_table(conn)

        create_posts_table(conn)
        create_post_vacancy_breakdown_table(conn)
        create_qualifications_table(conn)

        create_useful_links_table(conn)
        create_document_specs_table(conn)

        create_exams_table(conn)
        create_previous_year_papers_table(conn)
        create_cutoffs_table(conn)

        create_user_profiles_table(conn)
        create_alerts_sent_table(conn)

        create_scrape_logs_table(conn)

        conn.commit()
        logger.info("Database initialization complete. WAL mode active.")
    except Exception as e:
        conn.rollback()
        logger.error("Unexpected failure during init_db(): %s", e)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_db("gov_jobs.db")
