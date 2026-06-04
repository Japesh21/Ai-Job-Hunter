import json
import time
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone
from config.settings import JSEARCH_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://jsearch.p.rapidapi.com/search"
HEADERS = {
    "x-rapidapi-host": "jsearch.p.rapidapi.com",
    "x-rapidapi-key": JSEARCH_API_KEY,
    "Content-Type": "application/json",
}

MAX_AGE_DAYS = 30

SEARCH_QUERIES = [
    "python developer fresher India",
    "machine learning engineer fresher India",
    "data scientist fresher India",
    "software engineer fresher India",
    "web developer fresher India",
    "full stack developer fresher India",
    "data analyst fresher India",
    "AI engineer fresher India",
    "computer vision engineer fresher India",
    "QA engineer fresher India",
    "software tester fresher India",
    "data engineer fresher India",
    "backend developer fresher India",
    "react developer fresher India",
    "python intern India",
]

EXPERIENCE_BLOCK_PATTERNS = [
    "3+ years", "3+ yrs", "3 years experience", "4+ years", "4+ yrs",
    "5+ years", "5+ yrs", "5 years", "6+ years", "7+ years", "8+ years",
    "minimum 3", "minimum 4", "minimum 5",
    "at least 3 years", "at least 4 years",
    "three years experience", "four years experience", "five years experience",
]

TITLE_BLOCK_PATTERNS = [
    "senior", "sr ", "sr.", " lead", "lead ", "principal", "staff ",
    "manager", "head of", "director", "vp ", "vice president",
    "architect", "associate director", "consultant", " ii", " iii",
    "trainer", "teacher", "faculty", "professor",
    "sales", "marketing", "accountant", "finance", "hr ",
    "human resource", "recruiter", "content writer",
    "customer support", "customer service",
]

REMOTE_PHRASES = [
    "work from home", "work-from-home", "remote", "wfh",
    "fully remote", "work remotely", "anywhere in india",
    "anywhere", "virtual",
]

FRESHER_OVERRIDE_PHRASES = [
    "fresher", "freshers", "fresh graduate", "0-1 year", "0-2 year",
    "entry level", "entry-level", "no experience required", "recent graduate",
]

CLOSED_PHRASES = [
    "no longer accepting",
    "position has been filled",
    "position is filled",
    "this role has been filled",
    "vacancy has been filled",
    "not accepting applications",
    "closed to applications",
    "hiring is closed",
    "no longer available",
    "this position is closed",
]

# India country codes / names returned by JSearch
INDIA_IDENTIFIERS = {"india", "in", "ind", "bharat"}


def _load_blacklist() -> dict:
    path = Path(__file__).parent.parent.parent / "config" / "blacklist.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"blocked_companies": [], "blocked_keywords": []}


def _is_remote(location: str, description: str) -> bool:
    combined = f"{location} {description}".lower()
    return any(p in combined for p in REMOTE_PHRASES)


def _is_closed(description: str) -> bool:
    desc_lower = (description or "").lower()
    return any(p in desc_lower for p in CLOSED_PHRASES)


def _is_explicitly_fresher(title: str, description: str) -> bool:
    combined = f"{title} {description}".lower()
    return any(p in combined for p in FRESHER_OVERRIDE_PHRASES)


def _requires_too_much_experience(title: str, description: str) -> bool:
    title_lower = (title or "").lower()
    desc_lower  = (description or "").lower()
    if any(p in title_lower for p in TITLE_BLOCK_PATTERNS):
        return True
    if _is_explicitly_fresher(title, description):
        return False
    if any(p in desc_lower for p in EXPERIENCE_BLOCK_PATTERNS):
        return True
    return False


def _is_too_old(posted_at: str) -> bool:
    if not posted_at:
        return False
    try:
        posted = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - posted).days > MAX_AGE_DAYS
    except Exception:
        return False


def _is_non_india(job: dict) -> bool:
    """Return True if job is explicitly from outside India."""
    country = (job.get("job_country") or "").lower().strip()
    if not country:
        return False  # unknown → give benefit of doubt
    return country not in INDIA_IDENTIFIERS


def _fetch_query(query: str, pages: int = 3) -> list[dict]:
    results = []
    for page in range(1, pages + 1):
        params = {
            "query":      query,
            "page":       str(page),
            "num_pages":  "1",
            "country":    "in",
            "date_posted": "month",
        }
        try:
            time.sleep(1.5)
            resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=20)
            if resp.status_code == 429:
                logger.warning("JSearch rate limited — stopping query: %s", query)
                break
            if resp.status_code != 200:
                logger.warning("JSearch HTTP %d for query: %s", resp.status_code, query)
                continue
            data = resp.json()
            page_jobs = data.get("data", [])
            if not page_jobs:
                break
            results.extend(page_jobs)
        except Exception as e:
            logger.warning("JSearch fetch error for '%s': %s", query, e)
            break
    return results


def get_jobs() -> list[dict]:
    if not JSEARCH_API_KEY:
        logger.warning("JSEARCH_API_KEY not set — skipping JSearch scraper")
        return []

    seen_ids: set[str] = set()
    jobs = []
    skipped_exp      = 0
    skipped_remote   = 0
    skipped_old      = 0
    skipped_closed   = 0
    skipped_country  = 0
    skipped_blacklist = 0

    blacklist    = _load_blacklist()
    bl_keywords  = [kw.lower() for kw in blacklist.get("blocked_keywords", [])]
    bl_companies = [c.lower() for c in blacklist.get("blocked_companies", [])]

    for query in SEARCH_QUERIES:
        raw = _fetch_query(query)
        new_this_query = 0

        for job in raw:
            job_id = f"jsearch_{job.get('job_id', '')}"
            if not job_id or job_id in seen_ids:
                continue

            title       = job.get("job_title", "")
            company     = job.get("employer_name", "")
            city        = job.get("job_city") or ""
            location    = city or job.get("job_state") or job.get("job_country") or "India"
            description = job.get("job_description", "")
            url         = job.get("job_apply_link") or job.get("job_google_link") or ""
            posted_at   = job.get("job_posted_at_datetime_utc", "")
            emp_type    = (job.get("job_employment_type") or "").lower()
            job_type    = "internship" if ("intern" in emp_type or "intern" in title.lower()) else "job"

            # India-only filter
            if _is_non_india(job):
                skipped_country += 1
                continue

            # Age filter
            if _is_too_old(posted_at):
                skipped_old += 1
                continue

            # Closed job filter
            if _is_closed(description):
                skipped_closed += 1
                continue

            # Remote/WFH filter
            if _is_remote(location, description):
                skipped_remote += 1
                continue

            # Experience / seniority filter
            if _requires_too_much_experience(title, description):
                skipped_exp += 1
                continue

            # Blacklist filter
            combined = f"{title} {description}".lower()
            if any(kw in combined for kw in bl_keywords) or company.lower() in bl_companies:
                skipped_blacklist += 1
                continue

            seen_ids.add(job_id)
            new_this_query += 1

            jobs.append({
                "id":          job_id,
                "title":       title,
                "company":     company,
                "location":    location,
                "city":        city,
                "description": description,
                "url":         url,
                "source":      "jsearch",
                "job_type":    job_type,
                # Salary from JSearch is USD — store None to avoid INR threshold confusion
                "salary_min":  None,
                "salary_max":  None,
                "posted_at":   posted_at,
            })

        print(f"  [jsearch/{query[:30]}...]: {new_this_query} new jobs (raw: {len(raw)})")

    print(
        f"\nJSearch total: {len(jobs)} kept | "
        f"Blocked — country: {skipped_country}, closed: {skipped_closed}, "
        f"blacklist: {skipped_blacklist}, remote: {skipped_remote}, "
        f"exp: {skipped_exp}, old: {skipped_old}"
    )
    return jobs
