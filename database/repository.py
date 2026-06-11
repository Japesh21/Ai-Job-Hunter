import sqlite3
from typing import Optional
from utils.helpers import utcnow_iso
from database.connection import get_connection


# ── Jobs ────────────────────────────────────────────────────────────────────

def upsert_job(job: dict) -> None:
    sql = """
        INSERT INTO jobs (id, title, company, location, city, job_type, description, url, source,
                          salary_min, salary_max, posted_at, scraped_at)
        VALUES (:id, :title, :company, :location, :city, :job_type, :description, :url, :source,
                :salary_min, :salary_max, :posted_at, :scraped_at)
        ON CONFLICT(id) DO UPDATE SET
            title       = excluded.title,
            company     = excluded.company,
            location    = excluded.location,
            city        = excluded.city,
            job_type    = excluded.job_type,
            description = excluded.description,
            url         = excluded.url,
            source      = excluded.source,
            salary_min  = excluded.salary_min,
            salary_max  = excluded.salary_max,
            is_active   = 1
    """
    job.setdefault("scraped_at", utcnow_iso())
    job.setdefault("city", None)
    job.setdefault("job_type", None)
    with get_connection() as conn:
        conn.execute(sql, job)


def get_job(job_id: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()


def get_active_jobs(limit: int = 2000) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE is_active = 1 ORDER BY scraped_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


# ── Matched Jobs ─────────────────────────────────────────────────────────────

def save_match(job_id: str, score: float, notes: str = None) -> None:
    # Update score if already matched, insert if new — prevents duplicates across pipeline runs
    sql = """
        INSERT INTO matched_jobs (job_id, score, matched_at, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            score      = excluded.score,
            matched_at = excluded.matched_at
    """
    with get_connection() as conn:
        conn.execute(sql, (job_id, score, utcnow_iso(), notes))


def get_top_matches(limit: int = 20) -> list[sqlite3.Row]:
    sql = """
        SELECT j.*, m.score, m.matched_at
        FROM matched_jobs m
        JOIN jobs j ON j.id = m.job_id
        ORDER BY m.score DESC
        LIMIT ?
    """
    with get_connection() as conn:
        return conn.execute(sql, (limit,)).fetchall()


# ── Applications ─────────────────────────────────────────────────────────────

def add_application(job_id: str, resume_used: str = None, cover_letter: str = None, notes: str = None) -> int:
    sql = """
        INSERT INTO applications (job_id, applied_date, status, resume_used, cover_letter, notes, updated_at)
        VALUES (?, ?, 'applied', ?, ?, ?, ?)
    """
    now = utcnow_iso()
    with get_connection() as conn:
        cur = conn.execute(sql, (job_id, now, resume_used, cover_letter, notes, now))
        return cur.lastrowid


def update_application_status(app_id: int, status: str, notes: str = None) -> None:
    sql = "UPDATE applications SET status = ?, notes = ?, updated_at = ? WHERE id = ?"
    with get_connection() as conn:
        conn.execute(sql, (status, notes, utcnow_iso(), app_id))


def delete_application(app_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))


def get_applications(status: str = None) -> list[sqlite3.Row]:
    base = """
        SELECT a.*, j.title, j.company, j.location, j.city, j.url, j.source, j.job_type, j.salary_min, j.salary_max, j.posted_at as job_posted_at
        FROM applications a
        JOIN jobs j ON j.id = a.job_id
    """
    with get_connection() as conn:
        if status:
            return conn.execute(base + " WHERE a.status = ? ORDER BY a.applied_date DESC", (status,)).fetchall()
        return conn.execute(base + " ORDER BY a.applied_date DESC").fetchall()
