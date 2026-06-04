import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from config.settings import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, NOTIFY_EMAIL

logger = logging.getLogger(__name__)


def send_email(subject: str, body_html: str, to: str = None) -> bool:
    recipient = to or NOTIFY_EMAIL
    if not all([SMTP_USER, SMTP_PASS, recipient]):
        logger.warning("Email not configured — skipping send")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = recipient
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipient, msg.as_string())
        logger.info("Email sent to %s", recipient)
        return True
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        return False


def send_daily_report(jobs_scraped: int, jobs_matched: int, top_jobs: list[dict], applied_ids: set) -> bool:
    """
    Send daily job report email.
    top_jobs: list of dicts with keys: title, company, city, score, url
    applied_ids: set of job_ids already applied to — excluded from email
    """
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%d %b %Y")

    unapplied = [j for j in top_jobs if j.get("id") not in applied_ids]
    top_score = unapplied[0]["score"] if unapplied else 1.0
    if top_score == 0:
        top_score = 1.0

    # Build job rows
    job_rows = ""
    for job in unapplied[:20]:
        pct = int((job["score"] / top_score) * 100)
        bar_color = "#10b981" if pct >= 70 else "#3b82f6" if pct >= 40 else "#f59e0b"
        city = job.get("city") or job.get("location") or "India"
        company = job.get("company") or "—"
        url = job.get("url") or "#"
        title = job.get("title") or "—"

        job_rows += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #e2e8f0">
            <a href="{url}" style="color:#1e40af;font-weight:600;text-decoration:none;font-size:15px">{title}</a>
            <div style="color:#64748b;font-size:13px;margin-top:2px">🏢 {company} &nbsp;·&nbsp; 📍 {city}</div>
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid #e2e8f0;text-align:center">
            <span style="background:{bar_color};color:white;padding:3px 10px;border-radius:12px;font-weight:700;font-size:13px">{pct}%</span>
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid #e2e8f0;text-align:center">
            <a href="{url}" style="background:#1e40af;color:white;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600">Apply →</a>
          </td>
        </tr>"""

    if not job_rows:
        job_rows = '<tr><td colspan="3" style="padding:20px;text-align:center;color:#64748b">No new jobs today.</td></tr>'

    body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:system-ui,sans-serif">
  <div style="max-width:640px;margin:32px auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.08)">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);padding:28px 32px">
      <div style="color:white;font-size:22px;font-weight:700">🎯 AI Job Hunter</div>
      <div style="color:#bfdbfe;font-size:14px;margin-top:4px">Daily Report · {date_str}</div>
    </div>

    <!-- Stats -->
    <div style="display:flex;padding:20px 32px;background:#f8fafc;border-bottom:1px solid #e2e8f0">
      <div style="flex:1;text-align:center">
        <div style="font-size:28px;font-weight:700;color:#1e40af">{jobs_scraped}</div>
        <div style="font-size:12px;color:#64748b;margin-top:2px">Jobs Scraped</div>
      </div>
      <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0">
        <div style="font-size:28px;font-weight:700;color:#10b981">{jobs_matched}</div>
        <div style="font-size:12px;color:#64748b;margin-top:2px">Matched</div>
      </div>
      <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0">
        <div style="font-size:28px;font-weight:700;color:#f59e0b">{len(unapplied)}</div>
        <div style="font-size:12px;color:#64748b;margin-top:2px">New (unapplied)</div>
      </div>
    </div>

    <!-- Jobs table -->
    <div style="padding:24px 32px">
      <div style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:16px">Top Matches for You</div>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden">
        <thead>
          <tr style="background:#f8fafc">
            <th style="padding:10px 16px;text-align:left;font-size:12px;color:#64748b;font-weight:600;text-transform:uppercase">Job</th>
            <th style="padding:10px 16px;text-align:center;font-size:12px;color:#64748b;font-weight:600;text-transform:uppercase">Match</th>
            <th style="padding:10px 16px;text-align:center;font-size:12px;color:#64748b;font-weight:600;text-transform:uppercase">Link</th>
          </tr>
        </thead>
        <tbody>{job_rows}</tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center">
      <div style="color:#94a3b8;font-size:12px">AI Job Hunter · Japesh Mohan · Auto-generated daily report</div>
    </div>

  </div>
</body>
</html>"""

    subject = f"🎯 {len(unapplied)} New Job Matches — {date_str}"
    return send_email(subject, body)
