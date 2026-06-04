import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Paths
DB_PATH = BASE_DIR / "data" / "jobs.db"
RESUME_DIR = BASE_DIR / "data" / "resumes"
EXPORTS_DIR = BASE_DIR / "data" / "exports"
LOGS_DIR = BASE_DIR / "logs"

# API Keys
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")

# Email / Notifications
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "")

# Scraper behaviour
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RATE_LIMIT_DELAY = (1.0, 3.0)  # seconds, random between min/max
MAX_JOBS_PER_RUN = 200

# Matching thresholds
MIN_MATCH_SCORE = 0.08
COMPANIES_PER_RUN = 50   # career page scraper: companies per daily run
TOP_N_JOBS = 20

# Scheduler
SCRAPE_SCHEDULE_HOUR = 8   # 8 AM daily
REPORT_SCHEDULE_HOUR = 9   # 9 AM daily
