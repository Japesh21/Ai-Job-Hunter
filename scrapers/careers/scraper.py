"""
Playwright-based career page scraper.
Reads config/companies.csv, visits 50 companies per run (rotating).
Each company runs independently — failures are logged and skippable.
Use `python main.py scrape-retry` to rerun only failed companies.
"""
import csv
import json
import random
import logging
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from scrapers.careers.page_handler import (
    SEARCH_TERMS, try_search, extract_jobs_from_page
)

logger = logging.getLogger(__name__)

CONFIG_DIR       = Path(__file__).parent.parent.parent / "config"
CSV_PATH         = CONFIG_DIR / "companies.csv"
POINTER_PATH     = CONFIG_DIR / "company_pointer.txt"
FAILED_PATH      = CONFIG_DIR / "failed_companies.txt"
COMPANIES_PER_RUN = 50
PAGE_TIMEOUT      = 30_000   # ms per company
NAV_TIMEOUT       = 20_000   # ms for initial page load

# Same filters as other scrapers
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
    "trainee", "intern", "graduate",
]


def _load_blacklist() -> dict:
    path = CONFIG_DIR / "blacklist.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"blocked_companies": [], "blocked_keywords": []}


def _is_remote(location: str, title: str) -> bool:
    combined = f"{location} {title}".lower()
    return any(p in combined for p in REMOTE_PHRASES)


def _is_explicitly_fresher(title: str) -> bool:
    return any(p in title.lower() for p in FRESHER_OVERRIDE_PHRASES)


def _requires_too_much_experience(title: str) -> bool:
    title_lower = title.lower()
    if any(p in title_lower for p in TITLE_BLOCK_PATTERNS):
        return True
    if _is_explicitly_fresher(title):
        return False
    if any(p in title_lower for p in EXPERIENCE_BLOCK_PATTERNS):
        return True
    return False


def _load_companies() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _get_batch(companies: list[dict]) -> list[dict]:
    """Return next COMPANIES_PER_RUN companies, rotating through the full list."""
    start = 0
    if POINTER_PATH.exists():
        try:
            start = int(POINTER_PATH.read_text().strip())
        except Exception:
            start = 0

    batch = companies[start:start + COMPANIES_PER_RUN]
    # Handle wrap-around
    if len(batch) < COMPANIES_PER_RUN:
        batch += companies[:COMPANIES_PER_RUN - len(batch)]

    next_start = (start + COMPANIES_PER_RUN) % len(companies)
    POINTER_PATH.write_text(str(next_start))
    logger.info("Career scraper: processing companies %d-%d of %d",
                start, start + len(batch), len(companies))
    return batch


def _mark_failed(company: dict, reason: str) -> None:
    with open(FAILED_PATH, "a", encoding="utf-8") as f:
        f.write(f"{company['Company_Name']},{company['Career_Page']},{reason}\n")


def _load_failed_companies() -> list[dict]:
    if not FAILED_PATH.exists():
        return []
    companies = []
    with open(FAILED_PATH, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",", 2)
            if len(parts) >= 2:
                companies.append({"Company_Name": parts[0], "Career_Page": parts[1]})
    return companies


def _clear_failed() -> None:
    if FAILED_PATH.exists():
        FAILED_PATH.unlink()


def _apply_filters(jobs: list[dict], bl_keywords: list, bl_companies: list) -> list[dict]:
    """
    Filter career page jobs — IT/tech roles only, fresher/0-2 years.
    Career pages have no description so we filter on title only.
    We are inclusive of IT+business hybrid roles (e.g. business analyst,
    product analyst) but exclude pure non-tech (sales, HR, legal etc.)
    """
    # Must contain at least one of these to be considered IT-related
    IT_ROLE_WORDS = [
        "python", "java", "javascript", "react", "node", "angular", "vue",
        "data", "machine learning", "ml", "ai", "artificial intelligence",
        "software", "developer", "engineer", "programmer", "coder",
        "full stack", "fullstack", "backend", "frontend", "front end", "back end",
        "web", "mobile", "android", "ios", "flutter", "kotlin",
        "qa", "quality", "test", "automation", "sdet",
        "cloud", "devops", "aws", "azure", "gcp", "kubernetes", "docker",
        "database", "sql", "nosql", "mongodb", "postgresql",
        "analyst", "scientist", "computer vision", "nlp", "deep learning",
        "cybersecurity", "security", "network", "system", "infrastructure",
        "product", "technical", "technology", "digital", "it ",
        "intern", "trainee", "fresher", "graduate",
    ]

    # Hard block — clearly non-tech (even if at an IT company)
    NON_TECH_BLOCKS = [
        "sales", "marketing", "accountant", "finance", "legal", "lawyer",
        "hr ", "human resource", "recruiter", "talent acquisition",
        "customer support", "customer service", "customer success",
        "content writer", "graphic design", "video edit",
        "supply chain", "logistics", "warehouse", "operations executive",
        "hotel", "hospitality", "nurse", "doctor", "medical",
        "teacher", "faculty", "professor", "trainer",
    ]

    # Indian city/location keywords — job must mention one of these or be unspecified
    INDIA_LOCATION_HINTS = [
        "india", "bangalore", "bengaluru", "mumbai", "hyderabad", "chennai",
        "pune", "delhi", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad",
        "kochi", "trivandrum", "coimbatore", "jaipur", "chandigarh", "indore",
    ]

    # Non-India country mentions that mean it's NOT an India job
    NON_INDIA_COUNTRIES = [
        "united states", "usa", "u.s.", "uk ", "united kingdom", "canada",
        "australia", "germany", "france", "singapore", "uae", "dubai",
        "japan", "korea", "china", "netherlands", "sweden", "poland",
    ]

    filtered = []
    for job in jobs:
        # Normalize title — strip newlines that appear in some career page extractions
        raw_title = (job.get("title") or "").replace("\n", " ").replace("\r", " ").strip()
        # If title contains a newline-separated country prefix, clean it
        # e.g. "United States\n\nATE Test Engineer" → extract actual job part
        if "\n" in job.get("title", ""):
            parts = [p.strip() for p in job["title"].split("\n") if p.strip()]
            raw_title = parts[-1] if parts else raw_title

        title    = raw_title
        location = (job.get("location") or "").lower()
        company  = job.get("company", "").lower()
        title_l  = title.lower()
        combined = f"{title_l} {location}"

        # Skip jobs explicitly from non-India countries
        if any(c in combined for c in NON_INDIA_COUNTRIES):
            continue

        # Skip remote/WFH
        if _is_remote(location, title):
            continue

        # Skip senior/manager/non-tech seniority
        if _requires_too_much_experience(title):
            continue

        # Skip clearly non-tech roles
        if any(w in title_l for w in NON_TECH_BLOCKS):
            continue

        # Skip titles that are too short/vague to be real job listings
        if len(title.strip()) < 8:
            continue

        # Skip blacklisted
        if any(kw in title_l for kw in bl_keywords) or company in bl_companies:
            continue

        # Must be IT-related (broad — includes IT+business hybrid roles)
        if not any(w in title_l for w in IT_ROLE_WORDS):
            continue

        # Store cleaned title back into job
        job["title"] = title
        filtered.append(job)
    return filtered


def _scrape_company(company: dict, page) -> list[dict]:
    """Visit one company career page and extract jobs. Raises on failure."""
    from scrapers.careers.page_handler import URL_SEARCH_PATTERNS
    name = company["Company_Name"]
    url  = company["Career_Page"].rstrip("/")

    all_jobs = []

    # Strategy 1: Try URL-based search (faster — no typing needed)
    url_search_worked = False
    for pattern in URL_SEARCH_PATTERNS[:4]:
        search_url = url + pattern
        try:
            page.goto(search_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            jobs = extract_jobs_from_page(page, name)
            if len(jobs) >= 2:  # got real results
                all_jobs.extend(jobs)
                url_search_worked = True
                logger.debug("URL search worked for %s with pattern %s", name, pattern)
                break
        except Exception:
            continue

    # Strategy 2: Load main page and type in search box (if URL search failed)
    if not url_search_worked:
        page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        for term in SEARCH_TERMS[:2]:
            found_search = try_search(page, term)
            if found_search:
                page.wait_for_timeout(2000)
            jobs = extract_jobs_from_page(page, name)
            all_jobs.extend(jobs)
            if not found_search:
                break

    # Tag all jobs with metadata
    for job in all_jobs:
        job["source"]     = "careers"
        job["job_type"]   = (
            "internship" if any(w in job["title"].lower()
                                for w in ["intern", "internship", "trainee"])
            else "job"
        )
        job["salary_min"] = None
        job["salary_max"] = None
        job["posted_at"]  = ""
        # If no specific job URL was extracted, use the company career page URL
        if not job.get("url"):
            job["url"] = url
        job["id"] = f"careers_{name.lower().replace(' ', '_')}_{hash(job.get('url', job['title']))}"

    # Dedup by URL within this company
    seen_urls = set()
    unique = []
    for job in all_jobs:
        u = job.get("url", "")
        if u and u in seen_urls:
            continue
        seen_urls.add(u)
        unique.append(job)

    return unique


def _run_batch(companies: list[dict]) -> list[dict]:
    """Run Playwright scraper over a list of companies. Resilient — never crashes."""
    blacklist    = _load_blacklist()
    bl_keywords  = [kw.lower() for kw in blacklist.get("blocked_keywords", [])]
    bl_companies = [c.lower() for c in blacklist.get("blocked_companies", [])]

    all_jobs = []
    succeeded = failed = skipped = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT)

        for company in companies:
            name = company["Company_Name"]
            try:
                raw_jobs = _scrape_company(company, page)
                filtered = _apply_filters(raw_jobs, bl_keywords, bl_companies)
                all_jobs.extend(filtered)
                succeeded += 1
                print(f"  [careers/{name}]: {len(filtered)} jobs (raw: {len(raw_jobs)})")

            except PWTimeout:
                logger.warning("Timeout: %s — marking failed", name)
                _mark_failed(company, "timeout")
                failed += 1
                print(f"  [careers/{name}]: TIMEOUT — skipped")
                # Navigate away so next company starts clean
                try:
                    page.goto("about:blank", timeout=5000)
                except Exception:
                    pass

            except Exception as exc:
                logger.warning("Error on %s: %s", name, exc)
                _mark_failed(company, str(exc)[:80])
                failed += 1
                print(f"  [careers/{name}]: ERROR — {str(exc)[:60]}")
                try:
                    page.goto("about:blank", timeout=5000)
                except Exception:
                    pass

            # Polite delay between companies
            time.sleep(random.uniform(2.0, 4.0))

        context.close()
        browser.close()

    print(
        f"\nCareers total: {len(all_jobs)} jobs | "
        f"Companies — ok: {succeeded}, failed: {failed}, skipped: {skipped}"
    )
    if failed:
        print(f"  Failed companies saved to: {FAILED_PATH}")
        print("  Rerun failed: python main.py scrape-retry")

    return all_jobs


def get_jobs() -> list[dict]:
    """Main entry point — scrape next batch of companies from CSV."""
    if not CSV_PATH.exists():
        logger.warning("companies.csv not found at %s — skipping", CSV_PATH)
        return []

    companies = _load_companies()
    batch = _get_batch(companies)
    return _run_batch(batch)


def retry_failed() -> list[dict]:
    """Rerun only companies that failed in the last run."""
    companies = _load_failed_companies()
    if not companies:
        print("No failed companies to retry.")
        return []

    print(f"Retrying {len(companies)} failed companies...")
    _clear_failed()  # clear before retry so fresh failures are tracked
    jobs = _run_batch(companies)

    # Store retried jobs to DB
    from database.connection import init_db
    from database.repository import upsert_job
    init_db()
    for job in jobs:
        upsert_job(job)
    logger.info("Stored %d retried jobs", len(jobs))
    return jobs
