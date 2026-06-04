import logging
import schedule
import time
from config.settings import SCRAPE_SCHEDULE_HOUR, REPORT_SCHEDULE_HOUR
from notifications.alert_handler import send_crash_alert

logger = logging.getLogger(__name__)


def _safe_run(fn, name: str) -> None:
    try:
        fn()
    except Exception as exc:
        logger.error("Job '%s' failed: %s", name, exc)
        send_crash_alert(name, exc)


def register_jobs(scrape_fn, match_fn, all_fn) -> None:
    # Full pipeline (scrape + match + report + email) runs once daily at 8 AM
    schedule.every().day.at(f"{SCRAPE_SCHEDULE_HOUR:02d}:00").do(
        _safe_run, all_fn, "full-pipeline"
    )
    logger.info("Scheduler registered: full pipeline at %02d:00 daily", SCRAPE_SCHEDULE_HOUR)


def run_loop() -> None:
    logger.info("Scheduler running — press Ctrl+C to stop")
    while True:
        schedule.run_pending()
        time.sleep(30)
