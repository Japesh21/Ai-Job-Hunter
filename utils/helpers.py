import re
from datetime import datetime, timezone
from typing import Optional


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)          # strip HTML tags
    text = re.sub(r"\s+", " ", text)               # collapse whitespace
    return text.strip()


def parse_salary(raw: str) -> tuple[Optional[int], Optional[int]]:
    """Return (min_salary, max_salary) as ints, or (None, None) if unparseable."""
    if not raw:
        return None, None
    raw = raw.replace(",", "").replace("$", "")
    numbers = re.findall(r"\d+", raw)
    if not numbers:
        return None, None
    nums = [int(n) for n in numbers]
    # Assume hourly if all values < 500, convert to annual
    if all(n < 500 for n in nums):
        nums = [n * 2080 for n in nums]
    return (min(nums), max(nums)) if len(nums) >= 2 else (nums[0], nums[0])


def parse_date(raw: str) -> Optional[str]:
    """Try common date formats, return ISO 8601 string or None."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except (ValueError, AttributeError):
            continue
    return None


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text)


def truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
