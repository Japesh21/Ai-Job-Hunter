import json
import requests
from pathlib import Path
from datetime import datetime, timezone
from config.settings import ADZUNA_APP_ID, ADZUNA_APP_KEY

def _load_blacklist() -> dict:
    path = Path(__file__).parent.parent.parent / "config" / "blacklist.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"blocked_companies": [], "blocked_keywords": []}

BASE_URL = "https://api.adzuna.com/v1/api/jobs/in/search"

MAX_AGE_DAYS = 30
PAGES_PER_QUERY = 4  # 4 pages x 50 results = 200 per keyword

SALARY_MIN_INTERNSHIP = 15_000   # ₹/month
SALARY_MIN_JOB        = 30_000   # ₹/month

INTERN_TITLE_WORDS = ["intern", "internship", "trainee", "apprentice"]

# Each string is one Adzuna search query — results are merged and deduped
SEARCH_QUERIES = [
    # AI / ML / Data
    "python fresher",
    "machine learning fresher",
    "data engineer fresher",
    "junior data scientist",
    "junior machine learning",
    "computer vision fresher",
    "AI engineer fresher",
    "python entry level",
    "data analyst fresher",
    "deep learning fresher",
    "nlp fresher",
    "data science intern",
    "machine learning intern",
    # Web / Software
    "web developer fresher",
    "software engineer fresher",
    "junior python developer",
    "react developer fresher",
    "django developer fresher",
    "flask developer fresher",
    "node.js developer fresher",
    "full stack developer fresher",
    "frontend developer fresher",
    "backend developer fresher",
    # Mobile / Other Tech
    "android developer fresher",
    "flutter developer fresher",
    "java developer fresher",
    "cloud engineer fresher",
    "devops fresher",
    # QA / Testing
    "QA engineer fresher",
    "software tester fresher",
    "automation tester fresher",
    "test engineer fresher",
    "manual tester fresher",
    "SDET fresher",
    "QA analyst fresher",
    "junior QA engineer",
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

EXPERIENCE_BLOCK_PATTERNS = [
    # 3+ years variants
    "3+ years", "3+ yrs", "3 years experience", "3 yrs experience",
    "3years experience", "3-5 years", "3 to 5 years",
    # 4+ years variants
    "4+ years", "4+ yrs", "4 years experience", "4 yrs experience",
    # 5+ years variants
    "5+ years", "5+ yrs", "5 years experience", "5 yrs experience",
    "5 years", "6+ years", "7+ years", "8+ years", "9+ years",
    "10+ years", "10 years",
    # Written-out minimums
    "minimum 3", "minimum 4", "minimum 5",
    "at least 3 years", "at least 4 years", "at least 5 years",
    "minimum three", "minimum four", "minimum five",
    "three years experience", "four years experience", "five years experience",
    # Require fresher override — if job says fresher/0-2 yrs it stays regardless
]

TITLE_BLOCK_PATTERNS = [
    # Seniority
    "senior", "sr ", "sr.", " lead", "lead ", "principal", "staff ",
    "manager", "head of", "director", "vp ", "vice president",
    "architect", "associate director",
    "consultant", " ii", " iii", "level 2", "level 3",
    # Non-tech categories (synced with Internshala)
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
]


def _is_too_old(posted_at_str: str) -> bool:
    if not posted_at_str:
        return False
    try:
        posted = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - posted
        return age.days > MAX_AGE_DAYS
    except Exception:
        return False


def _is_closed(description: str) -> bool:
    if not description:
        return False
    desc_lower = description.lower()
    return any(phrase in desc_lower for phrase in CLOSED_PHRASES)


FRESHER_OVERRIDE_PHRASES = [
    "fresher", "freshers", "fresh graduate", "fresh graduates",
    "0-1 year", "0-2 year", "0 to 1 year", "0 to 2 year",
    "0-1 yrs", "0-2 yrs", "zero experience", "no experience required",
    "recent graduate", "entry level", "entry-level",
]


REMOTE_PHRASES = [
    "work from home", "work-from-home", "remote", "wfh",
    "fully remote", "work remotely", "anywhere in india",
    "anywhere", "virtual",
]


def _is_remote(location: str, description: str) -> bool:
    """Return True if job is remote/WFH — blocked for onsite-only search."""
    combined = f"{location} {description}".lower()
    return any(p in combined for p in REMOTE_PHRASES)


def _is_explicitly_fresher(title: str, description: str) -> bool:
    """Return True if the job explicitly targets freshers — skip exp block if so."""
    combined = f"{title} {description}".lower()
    return any(phrase in combined for phrase in FRESHER_OVERRIDE_PHRASES)


def _requires_too_much_experience(title: str, description: str) -> bool:
    title_lower = (title or "").lower()
    desc_lower = (description or "").lower()

    # Block seniority in title regardless
    if any(pat in title_lower for pat in TITLE_BLOCK_PATTERNS):
        return True

    # If job explicitly says fresher/0-2 yrs, trust it over experience mentions
    if _is_explicitly_fresher(title, description):
        return False

    if any(pat in desc_lower for pat in EXPERIENCE_BLOCK_PATTERNS):
        return True

    return False


def _fetch_query(keyword: str, pages: int) -> list[dict]:
    results = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/{page}"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 50,
            "what": keyword,
            "where": "India",
            "sort_by": "date",
            "content-type": "application/json",
        }
        try:
            response = requests.get(url, params=params, timeout=20)
            if response.status_code == 429:
                print(f"  [{keyword}] page {page}: rate limited, stopping query")
                break
            if response.status_code != 200:
                print(f"  [{keyword}] page {page}: HTTP {response.status_code}, skipping")
                continue
            data = response.json()
            page_results = data.get("results", [])
            if not page_results:
                break
            results.extend(page_results)
        except Exception as e:
            print(f"  [{keyword}] page {page} error: {e}")
            break
    return results


def get_jobs() -> list[dict]:
    seen_ids: set[str] = set()
    jobs = []
    skipped_exp = skipped_closed = skipped_old = skipped_remote = skipped_blacklist = skipped_salary = 0
    blacklist = _load_blacklist()
    bl_keywords = [kw.lower() for kw in blacklist.get("blocked_keywords", [])]
    bl_companies = [c.lower() for c in blacklist.get("blocked_companies", [])]

    for keyword in SEARCH_QUERIES:
        raw = _fetch_query(keyword, PAGES_PER_QUERY)
        new_this_query = 0

        for job in raw:
            job_id = str(job.get("id", ""))
            if not job_id or job_id in seen_ids:
                continue

            title = job.get("title", "")
            description = job.get("description", "")
            posted_at = job.get("created", "")
            location_data = job.get("location", {})

            if _is_too_old(posted_at):
                skipped_old += 1
                continue
            if _is_closed(description):
                skipped_closed += 1
                continue
            if _requires_too_much_experience(title, description):
                skipped_exp += 1
                continue
            if _is_remote(location_data.get("display_name", ""), description):
                skipped_remote += 1
                continue

            # Blacklist filter — keywords and companies
            combined = f"{title} {description}".lower()
            company = job.get("company", {}).get("display_name", "").lower()
            if any(kw in combined for kw in bl_keywords) or company in bl_companies:
                skipped_blacklist += 1
                continue

            # Job type detection
            title_lower = title.lower()
            job_type = "internship" if any(w in title_lower for w in INTERN_TITLE_WORDS) else "job"

            # Salary filter — Adzuna returns annual INR salary
            sal_min = job.get("salary_min")
            sal_max = job.get("salary_max")
            if sal_min is not None:
                monthly = int(sal_min) // 12
                threshold = SALARY_MIN_INTERNSHIP if job_type == "internship" else SALARY_MIN_JOB
                if monthly < threshold:
                    skipped_salary += 1
                    continue

            seen_ids.add(job_id)
            new_this_query += 1

            area = location_data.get("area", [])
            city = area[-1] if area else location_data.get("display_name", "")

            jobs.append({
                "id":          job_id,
                "title":       title,
                "company":     job.get("company", {}).get("display_name", ""),
                "location":    location_data.get("display_name", ""),
                "city":        city,
                "description": description,
                "url":         job.get("redirect_url", ""),
                "source":      "adzuna",
                "job_type":    job_type,
                "salary_min":  sal_min,
                "salary_max":  sal_max,
                "posted_at":   posted_at,
            })

        print(f"  [{keyword}]: {new_this_query} new jobs (total raw: {len(raw)})")

    print(
        f"\nTotal kept: {len(jobs)} | "
        f"Blocked — salary: {skipped_salary}, blacklist: {skipped_blacklist}, "
        f"remote: {skipped_remote}, exp: {skipped_exp}, closed: {skipped_closed}, old: {skipped_old}"
    )
    return jobs
