import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path("logs") / "app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_scrape():
    logger.info("Starting scrape run...")
    from scrapers.adzuna.scraper import get_jobs as adzuna_jobs
    from scrapers.internshala.scraper import get_jobs as internshala_jobs
    from scrapers.jsearch.scraper import get_jobs as jsearch_jobs
    from database.repository import upsert_job

    jobs = []

    logger.info("Scraping Adzuna...")
    try:
        jobs += adzuna_jobs()
    except Exception as e:
        logger.error("Adzuna scraper failed: %s", e)

    logger.info("Scraping Internshala...")
    try:
        jobs += internshala_jobs()
    except Exception as e:
        logger.error("Internshala scraper failed: %s", e)

    logger.info("Scraping JSearch (LinkedIn/Indeed/Glassdoor)...")
    try:
        jobs += jsearch_jobs()
    except Exception as e:
        logger.error("JSearch scraper failed: %s", e)

    logger.info("Scraping company career pages (Playwright)...")
    try:
        from scrapers.careers.scraper import get_jobs as careers_jobs
        jobs += careers_jobs()
    except Exception as e:
        logger.error("Careers scraper failed: %s", e)

    # Cross-scraper dedup by URL — same job appearing on multiple sources stored once
    seen_urls: set = set()
    deduped = []
    for job in jobs:
        url = (job.get("url") or "").split("?")[0].rstrip("/")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        deduped.append(job)
    dupes_removed = len(jobs) - len(deduped)
    if dupes_removed:
        logger.info("Cross-source dedup removed %d duplicate jobs", dupes_removed)
    jobs = deduped

    logger.info("Total fetched: %d jobs", len(jobs))
    for job in jobs:
        upsert_job(job)
    logger.info("Stored %d jobs in database", len(jobs))


def run_match():
    logger.info("Starting match run...")
    from resume.profile_builder import build_profile
    from matching.scorer import filter_jobs
    from database.repository import get_active_jobs, save_match

    profile = build_profile()
    jobs = [dict(j) for j in get_active_jobs()]
    logger.info("Loaded %d jobs from database", len(jobs))

    matches = filter_jobs(jobs, profile)
    logger.info("Found %d matching jobs", len(matches))

    for job in matches:
        save_match(job["id"], job["_score"])


def run_report():
    logger.info("Generating report...")
    from reports.html_report import generate_html_report
    from reports.csv_exporter import export_matches_csv
    html_path = generate_html_report()
    csv_path = export_matches_csv()
    logger.info("Report: %s | CSV: %s", html_path, csv_path)


def run_email():
    logger.info("Sending daily email report...")
    from database.repository import get_active_jobs, get_top_matches, get_applications
    from notifications.email_sender import send_daily_report

    # Read actual counts from DB so this works even when called standalone
    jobs_in_db  = len(get_active_jobs())
    top_jobs    = [dict(j) for j in get_top_matches(limit=50)]
    applied_ids = {a["job_id"] for a in get_applications()}

    ok = send_daily_report(
        jobs_scraped=jobs_in_db,
        jobs_matched=len(top_jobs),
        top_jobs=top_jobs,
        applied_ids=applied_ids,
    )
    if ok:
        logger.info("Email sent successfully")
    else:
        logger.warning("Email failed — check SMTP settings in .env")


def run_all():
    run_scrape()
    run_match()
    run_report()
    run_email()


def run_scheduler():
    from scheduler.scheduler import register_jobs, run_loop
    register_jobs(run_scrape, run_match, run_all)
    run_loop()


def main():
    parser = argparse.ArgumentParser(description="AI Job Hunter")
    parser.add_argument(
        "command",
        choices=["scrape", "match", "report", "email", "schedule", "all", "scrape-retry"],
        help="Command to run",
    )
    args = parser.parse_args()

    from database.connection import init_db
    init_db()

    if args.command == "scrape":
        run_scrape()
    elif args.command == "match":
        run_match()
    elif args.command == "report":
        run_report()
    elif args.command == "email":
        run_email()
    elif args.command == "schedule":
        run_scheduler()
    elif args.command == "all":
        run_all()
    elif args.command == "scrape-retry":
        from scrapers.careers.scraper import retry_failed
        retry_failed()


if __name__ == "__main__":
    main()
