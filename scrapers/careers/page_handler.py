"""
Generic Playwright page interaction for career pages.
Tries multiple strategies to find job listings since every company has different HTML.
"""
import re
import logging
from playwright.sync_api import Page, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

# Role keywords searched on each career page
# These are typed into the site's own search box
SEARCH_TERMS = [
    "fresher",
    "entry level",
    "0-2 years",
    "junior developer",
    "junior engineer",
]

# URL query param patterns many career sites support
# We try appending these to the career page URL first (faster than typing)
URL_SEARCH_PATTERNS = [
    "?q=fresher",
    "?keyword=fresher",
    "?keywords=fresher",
    "?search=fresher",
    "?query=fresher",
    "/search?q=fresher",
    "/jobs?keyword=fresher",
    "/jobs?q=fresher",
]

# CSS selectors that commonly contain job search inputs
SEARCH_BOX_SELECTORS = [
    'input[placeholder*="job" i]',
    'input[placeholder*="search" i]',
    'input[placeholder*="keyword" i]',
    'input[placeholder*="role" i]',
    'input[placeholder*="position" i]',
    'input[type="search"]',
    'input[name*="keyword" i]',
    'input[name*="search" i]',
    'input[name*="query" i]',
    'input[id*="search" i]',
    'input[id*="keyword" i]',
    'input[class*="search" i]',
]

# CSS selectors that commonly wrap job cards
JOB_CARD_SELECTORS = [
    '[class*="job-card"]',
    '[class*="job-item"]',
    '[class*="job-listing"]',
    '[class*="job-result"]',
    '[class*="position-card"]',
    '[class*="opening-card"]',
    '[class*="career-card"]',
    '[data-job-id]',
    '[data-position-id]',
    'article[class*="job"]',
    'li[class*="job"]',
    'div[class*="joblist"] > div',
    'div[class*="job_list"] > div',
    'div[class*="jobs-list"] > div',
    'table[class*="job"] tr',
]

# Title element selectors within a job card
TITLE_SELECTORS = [
    'h1', 'h2', 'h3', 'h4',
    '[class*="job-title"]',
    '[class*="position-title"]',
    '[class*="role-title"]',
    '[class*="title"]',
    'a[href*="job"]',
    'a[href*="career"]',
]

# Location selectors within a job card
LOCATION_SELECTORS = [
    '[class*="location"]',
    '[class*="city"]',
    '[class*="place"]',
    '[data-location]',
    'span[class*="loc"]',
]


def try_search(page: Page, term: str) -> bool:
    """Try to type a search term into a search box. Returns True if found a box."""
    for selector in SEARCH_BOX_SELECTORS:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.triple_click()
                el.type(term, delay=50)
                # Press Enter or click a search button
                try:
                    page.keyboard.press("Enter")
                except Exception:
                    pass
                try:
                    btn = page.query_selector(
                        'button[type="submit"], button[class*="search"], '
                        'input[type="submit"], [class*="search-btn"]'
                    )
                    if btn:
                        btn.click()
                except Exception:
                    pass
                page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    return False


def extract_jobs_from_page(page: Page, company_name: str) -> list[dict]:
    """Try multiple strategies to extract job listings from the current page."""
    jobs = []

    # Strategy 1: look for job card containers
    for card_selector in JOB_CARD_SELECTORS:
        try:
            cards = page.query_selector_all(card_selector)
            if len(cards) >= 2:  # need at least 2 to be meaningful
                for card in cards[:30]:  # max 30 per page
                    job = _extract_from_card(card, company_name, page.url)
                    if job:
                        jobs.append(job)
                if jobs:
                    logger.debug("Found %d jobs via card selector: %s", len(jobs), card_selector)
                    return jobs
        except Exception:
            continue

    # Strategy 2: find all links that look like job postings
    if not jobs:
        jobs = _extract_from_links(page, company_name)

    return jobs


def _extract_from_card(card, company_name: str, base_url: str) -> dict | None:
    """Extract job info from a single card element."""
    try:
        # Get title
        title = ""
        for sel in TITLE_SELECTORS:
            el = card.query_selector(sel)
            if el:
                t = el.inner_text().strip()
                if t and 5 < len(t) < 150:
                    title = t
                    break

        if not title:
            return None

        # Get URL
        url = ""
        link = card.query_selector("a[href]")
        if link:
            href = link.get_attribute("href") or ""
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                # Build absolute URL
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                url = f"{parsed.scheme}://{parsed.netloc}{href}"

        # Get location
        location = "India"
        for sel in LOCATION_SELECTORS:
            el = card.query_selector(sel)
            if el:
                loc = el.inner_text().strip()
                if loc and len(loc) < 100:
                    location = loc
                    break

        return {
            "title": title,
            "company": company_name,
            "location": location,
            "city": location.split(",")[-1].strip() if "," in location else location,
            "url": url,
            "description": title,  # minimal — career pages rarely show full desc in listing
        }
    except Exception:
        return None


def _extract_from_links(page: Page, company_name: str) -> list[dict]:
    """Fallback: find all <a> tags whose text looks like a job title."""
    jobs = []
    job_keywords = ["engineer", "developer", "analyst", "scientist", "intern",
                    "fresher", "trainee", "associate", "specialist"]
    try:
        links = page.query_selector_all("a[href]")
        for link in links[:200]:
            try:
                text = (link.inner_text() or "").strip()
                href = link.get_attribute("href") or ""
                if (10 < len(text) < 120
                        and any(kw in text.lower() for kw in job_keywords)
                        and ("job" in href.lower() or "career" in href.lower()
                             or "position" in href.lower() or "opening" in href.lower())):

                    if href.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(page.url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"

                    jobs.append({
                        "title": text,
                        "company": company_name,
                        "location": "India",
                        "city": "India",
                        "url": href,
                        "description": text,
                    })
            except Exception:
                continue
    except Exception:
        pass
    return jobs[:20]
