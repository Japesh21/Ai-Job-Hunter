import re
import json
import time
import random
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup


def _load_blacklist() -> dict:
    path = Path(__file__).parent.parent.parent / "config" / "blacklist.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"blocked_companies": [], "blocked_keywords": []}

logger = logging.getLogger(__name__)

BASE_URL = "https://internshala.com"
MAX_PAGES = 5
MAX_AGE_DAYS = 30

# Salary thresholds (monthly, INR)
SALARY_MIN_INTERNSHIP = 15_000
SALARY_MIN_JOB       = 30_000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SEARCH_PATHS = [
    "/jobs/fresher-jobs",
    "/jobs/python-jobs",
    "/jobs/machine-learning-jobs",
    "/jobs/data-science-jobs",
    "/jobs/web-development-jobs",
    "/jobs/software-development-jobs",
    "/jobs/computer-vision-jobs",
    "/jobs/data-analyst-jobs",
    "/jobs/artificial-intelligence-jobs",
    "/jobs/qa-jobs",
    "/jobs/software-testing-jobs",
    "/jobs/full-stack-development-jobs",
]

EXPERIENCE_BLOCK_PATTERNS = [
    # 3 years variants (synced with Adzuna)
    "3+ years", "3+ yrs", "3 years experience", "3 yrs experience",
    "3-5 years", "3 to 5 years",
    # 4 years
    "4+ years", "4+ yrs", "4 years experience", "4 yrs experience",
    # 5+ years
    "5+ years", "5+ yrs", "5 years experience", "5 yrs experience", "5 years",
    # 6-10 years
    "6+ years", "7+ years", "8+ years", "9+ years", "10+ years", "10 years",
    # Written-out
    "minimum 3", "minimum 4", "minimum 5",
    "at least 3 years", "at least 4 years", "at least 5 years",
    "minimum three", "minimum four", "minimum five",
    "three years experience", "four years experience", "five years experience",
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

TITLE_BLOCK_PATTERNS = [
    "senior", "sr ", "sr.", " lead", "lead ", "principal", "staff ",
    "manager", "head of", "director", "vp ", "vice president",
    "architect", "associate director",
    "trainer", "teacher", "faculty", "professor", "tutor",
    "sales", "marketing", "accountant", "finance", "hr ",
    "human resource", "recruiter", "content writer", "seo",
    "customer support", "customer service", "telecaller",
    "pilates", "yoga", "fitness", "instructor", "chef", "cook",
    "hotel", "hospitality", "front office", "reservation", "housekeep",
    "nurse", "doctor", "medical", "pharma", "clinical",
    "legal", "lawyer", "advocate", "compliance",
    "video editor", "graphic design", "animator", "illustrat",
    "operations executive", "operations manager", "supply chain",
    "logistics", "warehouse", "field sales",
    "regulatory",
    # "research assistant" removed — legitimate CS/data entry-level role
]

FRESHER_OVERRIDE_PHRASES = [
    "fresher", "freshers", "fresh graduate", "0-1 year", "0-2 year",
    "0 to 1 year", "0 to 2 year", "no experience required",
    "recent graduate", "entry level", "entry-level",
]

# Phrases that mean the job is remote/WFH — block these
REMOTE_PHRASES = [
    "work from home", "work-from-home", "remote", "wfh",
    "anywhere in india", "anywhere", "virtual",
]


def _is_remote(location: str, description: str = "") -> bool:
    """Return True if job is remote/WFH — should be blocked for onsite-only search."""
    # Internshala uses "Work from home" directly as the location text
    loc_lower = (location or "").lower()
    if any(p in loc_lower for p in REMOTE_PHRASES):
        return True
    # Also check description for remote mentions
    desc_lower = (description or "").lower()
    return any(p in desc_lower for p in ["fully remote", "100% remote", "work from home"])

# Salary text that means "we won't tell you" → give benefit of doubt, keep job
SALARY_UNDISCLOSED_PHRASES = [
    "competitive", "not disclosed", "negotiable", "as per industry",
    "as per company", "best in industry", "market standard", "",
]


def _parse_internshala_salary(raw: str) -> int | None:
    """
    Parse Internshala salary text to monthly INR integer.
    Returns None if undisclosed/competitive (caller keeps the job).
    Returns integer if numeric (caller compares to threshold).
    """
    if not raw:
        return None

    cleaned = raw.lower().strip()

    # Undisclosed — give benefit of doubt
    if any(phrase in cleaned for phrase in SALARY_UNDISCLOSED_PHRASES):
        return None

    # Remove currency symbols, commas, spaces
    cleaned = re.sub(r"[₹,\s]", "", cleaned)

    # Extract all digit groups
    numbers = re.findall(r"\d+", cleaned)
    if not numbers:
        return None

    # Take the minimum (first) number as the lower bound
    amount = int(numbers[0])

    # If annual figure (> 5 lakh), convert to monthly
    if amount > 500_000:
        amount = amount // 12

    return amount


def _parse_job_type(card) -> str:
    """Return 'internship' or 'job' based on Internshala gray label."""
    gray = card.find("div", class_="gray-labels")
    if gray:
        text = gray.get_text(separator=" ", strip=True).lower()
        if "internship" in text:
            return "internship"
    return "job"


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


def _parse_posted_date(posted_text: str) -> str:
    now  = datetime.now(timezone.utc)
    text = (posted_text or "").lower().strip()
    try:
        if "day"   in text:
            n = int("".join(filter(str.isdigit, text)) or "1")
            return (now - timedelta(days=n)).isoformat()
        if "week"  in text:
            n = int("".join(filter(str.isdigit, text)) or "1")
            return (now - timedelta(weeks=n)).isoformat()
        if "month" in text:
            n = int("".join(filter(str.isdigit, text)) or "1")
            return (now - timedelta(days=n * 30)).isoformat()
        if "hour" in text or "just" in text or "today" in text:
            return now.isoformat()
    except Exception:
        pass
    return now.isoformat()


def _is_too_old(posted_iso: str) -> bool:
    """Accepts already-parsed ISO string (output of _parse_posted_date)."""
    try:
        posted = datetime.fromisoformat(posted_iso)
        return (datetime.now(timezone.utc) - posted).days > MAX_AGE_DAYS
    except Exception:
        return False


def _fetch_page(path: str, page: int) -> BeautifulSoup | None:
    url = f"{BASE_URL}{path}/" if page == 1 else f"{BASE_URL}{path}/page-{page}/"
    try:
        time.sleep(random.uniform(1.5, 3.0))
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning("Internshala %s page %d: HTTP %d", path, page, resp.status_code)
            return None
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.warning("Internshala fetch error %s page %d: %s", path, page, e)
        return None


def _parse_cards(soup: BeautifulSoup) -> list[dict]:
    jobs = []
    for card in soup.find_all("div", class_="individual_internship"):
        try:
            job_id_raw = card.get("internshipid") or card.get("id", "")
            job_id = f"internshala_{job_id_raw}"

            title_tag = card.find("a", class_="job-title-href")
            title = title_tag.get_text(strip=True) if title_tag else ""
            if not title:
                continue

            href = card.get("data-href") or (title_tag.get("href") if title_tag else "")
            url  = f"{BASE_URL}{href}" if href and href.startswith("/") else href or ""

            company_tag = card.find("p", class_="company-name")
            company = company_tag.get_text(strip=True) if company_tag else ""

            loc_tag  = card.find("p", class_="locations")
            location = loc_tag.get_text(strip=True).replace("\n", " ").strip() if loc_tag else "India"
            city     = location.split(",")[-1].strip() if "," in location else location

            # Salary raw text
            salary_raw = ""
            for row_item in card.find_all("div", class_="row-1-item"):
                if row_item.find("i", class_="ic-16-money"):
                    salary_raw = row_item.get_text(strip=True)
                    break

            # Job type (internship vs full-time job)
            job_type = _parse_job_type(card)

            desc_tag    = card.find("div", class_="about_job")
            description = desc_tag.get_text(separator=" ", strip=True) if desc_tag else ""

            posted_tag  = card.find("div", class_="status-inactive")
            posted_text = posted_tag.get_text(strip=True) if posted_tag else ""
            posted_at   = _parse_posted_date(posted_text)

            # Parse numeric salary for filtering
            salary_monthly = _parse_internshala_salary(salary_raw)

        except Exception as e:
            logger.debug("Card parse error: %s", e)
            continue

        jobs.append({
            "id":          job_id,
            "title":       title,
            "company":     company,
            "location":    location,
            "city":        city,
            "description": description,
            "url":         url,
            "source":      "internshala",
            "job_type":    job_type,
            "salary_min":  salary_monthly,   # None if undisclosed, int if stated
            "salary_max":  None,
            "posted_at":   posted_at,
        })

    return jobs


def get_jobs() -> list[dict]:
    seen_ids: set[str] = set()
    all_jobs = []
    skipped_exp       = 0
    skipped_old       = 0
    skipped_salary    = 0
    skipped_remote    = 0
    skipped_closed    = 0
    skipped_blacklist = 0
    blacklist   = _load_blacklist()
    bl_keywords = [kw.lower() for kw in blacklist.get("blocked_keywords", [])]
    bl_companies = [c.lower() for c in blacklist.get("blocked_companies", [])]

    for path in SEARCH_PATHS:
        new_this_path = 0

        for page in range(1, MAX_PAGES + 1):
            soup = _fetch_page(path, page)
            if soup is None:
                break

            cards = _parse_cards(soup)
            if not cards:
                break

            for job in cards:
                job_id = job["id"]
                if job_id in seen_ids:
                    continue

                # Remote/WFH filter — onsite India only
                if _is_remote(job["location"], job["description"]):
                    skipped_remote += 1
                    continue

                # Closed job filter
                desc_lower = job["description"].lower()
                if any(p in desc_lower for p in CLOSED_PHRASES):
                    skipped_closed += 1
                    continue

                # Age filter
                if _is_too_old(job.get("posted_at", "")):
                    skipped_old += 1
                    continue

                # Experience / seniority filter
                if _requires_too_much_experience(job["title"], job["description"]):
                    skipped_exp += 1
                    continue

                # Salary filter — only when salary is explicitly stated
                salary = job["salary_min"]
                if salary is not None:
                    threshold = SALARY_MIN_INTERNSHIP if job["job_type"] == "internship" else SALARY_MIN_JOB
                    if salary < threshold:
                        skipped_salary += 1
                        logger.debug(
                            "Salary blocked: %s — ₹%d/mo (need ₹%d, type=%s)",
                            job["title"], salary, threshold, job["job_type"],
                        )
                        continue

                # Blacklist filter — keywords and companies
                combined = f"{job['title']} {job['description']}".lower()
                company  = job.get("company", "").lower()
                if any(kw in combined for kw in bl_keywords) or company in bl_companies:
                    skipped_blacklist += 1
                    continue

                seen_ids.add(job_id)
                new_this_path += 1
                all_jobs.append(job)

            last_page = soup.find("input", {"id": "isLastPage"})
            if last_page and last_page.get("value") == "true":
                break

        logger.info("  [internshala%s]: %d new jobs", path, new_this_path)
        print(f"  [internshala{path}]: {new_this_path} new jobs")

    print(
        f"\nInternshala total: {len(all_jobs)} kept | "
        f"Blocked — blacklist: {skipped_blacklist}, remote: {skipped_remote}, "
        f"closed: {skipped_closed}, exp: {skipped_exp}, salary: {skipped_salary}, old: {skipped_old}"
    )
    return all_jobs
