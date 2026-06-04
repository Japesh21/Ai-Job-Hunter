import logging
import traceback
from notifications.email_sender import send_email

logger = logging.getLogger(__name__)


def send_crash_alert(component: str, error: Exception) -> None:
    subject = f"[AI-Job-Hunter] CRASH in {component}"
    tb = traceback.format_exc()
    body = f"""
    <h2>Component crashed: {component}</h2>
    <p><b>Error:</b> {type(error).__name__}: {error}</p>
    <pre>{tb}</pre>
    """
    send_email(subject, body)
    logger.error("Crash alert sent for %s: %s", component, error)


def send_run_summary(jobs_found: int, jobs_matched: int, errors: list[str] = None) -> None:
    status = "OK" if not errors else "PARTIAL"
    subject = f"[AI-Job-Hunter] Daily Run [{status}] — {jobs_matched} matches"
    error_block = ""
    if errors:
        items = "".join(f"<li>{e}</li>" for e in errors)
        error_block = f"<h3>Errors</h3><ul>{items}</ul>"

    body = f"""
    <h2>Daily scrape complete</h2>
    <ul>
      <li>Jobs scraped: <b>{jobs_found}</b></li>
      <li>Jobs matched: <b>{jobs_matched}</b></li>
    </ul>
    {error_block}
    """
    send_email(subject, body)
