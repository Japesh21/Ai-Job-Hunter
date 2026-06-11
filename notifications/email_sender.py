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
        print(f"EMAIL ERROR: {exc}", flush=True)
        return False


def _build_job_row(job: dict, top_score: float) -> str:
    pct       = int((job["score"] / top_score) * 100)
    bar_color = "#10b981" if pct >= 70 else "#3b82f6" if pct >= 40 else "#f59e0b"
    city      = job.get("city") or job.get("location") or "India"
    company   = job.get("company") or "—"
    url       = job.get("url") or "#"
    title     = job.get("title") or "—"
    source    = (job.get("source") or "").capitalize()
    jtype     = job.get("job_type") or ""
    type_tag  = "🎓" if jtype == "internship" else "💼"

    return f"""
    <tr>
      <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0">
        <a href="{url}" style="color:#1e40af;font-weight:600;text-decoration:none;font-size:14px">{title}</a>
        <div style="color:#64748b;font-size:12px;margin-top:2px">
          🏢 {company} &nbsp;·&nbsp; 📍 {city} &nbsp;·&nbsp; {type_tag} {source}
        </div>
      </td>
      <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;text-align:center;white-space:nowrap">
        <span style="background:{bar_color};color:white;padding:2px 8px;border-radius:10px;font-weight:700;font-size:12px">{pct}%</span>
      </td>
      <td style="padding:10px 14px;border-bottom:1px solid #e2e8f0;text-align:center">
        <a href="{url}" style="background:#1e40af;color:white;padding:5px 12px;border-radius:5px;text-decoration:none;font-size:12px;font-weight:600">Apply →</a>
      </td>
    </tr>"""


def send_daily_report(jobs_scraped: int, jobs_matched: int, top_jobs: list[dict], applied_ids: set) -> bool:
    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%d %b %Y")

    # All unapplied jobs — no cap
    unapplied = [j for j in top_jobs if j.get("id") not in applied_ids]
    top_score = unapplied[0]["score"] if unapplied else 1.0
    if top_score == 0:
        top_score = 1.0

    # Group by source for readability
    SOURCE_ORDER  = ["adzuna", "internshala", "jsearch", "careers"]
    SOURCE_LABELS = {
        "adzuna":      "🔵 Adzuna",
        "internshala": "🟠 Internshala",
        "jsearch":     "🟢 JSearch (LinkedIn/Indeed)",
        "careers":     "🏢 Company Career Pages",
    }

    sections_html = ""
    total_shown   = 0

    for src in SOURCE_ORDER:
        src_jobs = [j for j in unapplied if (j.get("source") or "") == src]
        if not src_jobs:
            continue

        label = SOURCE_LABELS.get(src, src.capitalize())
        rows  = "".join(_build_job_row(j, top_score) for j in src_jobs)
        total_shown += len(src_jobs)

        sections_html += f"""
    <div style="padding:20px 28px 0">
      <div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:12px;padding-bottom:6px;border-bottom:2px solid #e2e8f0">
        {label} &nbsp;<span style="font-size:13px;font-weight:400;color:#64748b">({len(src_jobs)} jobs)</span>
      </div>
      <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;margin-bottom:8px">
        <thead>
          <tr style="background:#f8fafc">
            <th style="padding:8px 14px;text-align:left;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Job</th>
            <th style="padding:8px 14px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Match</th>
            <th style="padding:8px 14px;text-align:center;font-size:11px;color:#64748b;font-weight:600;text-transform:uppercase">Link</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

    if not sections_html:
        sections_html = '<div style="padding:24px;text-align:center;color:#64748b">No new jobs today.</div>'

    body = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:system-ui,sans-serif">
  <div style="max-width:700px;margin:24px auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.08)">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);padding:24px 28px">
      <div style="color:white;font-size:20px;font-weight:700">🎯 AI Job Hunter</div>
      <div style="color:#bfdbfe;font-size:13px;margin-top:3px">Daily Report · {date_str}</div>
    </div>

    <!-- Stats -->
    <div style="display:flex;padding:16px 28px;background:#f8fafc;border-bottom:1px solid #e2e8f0">
      <div style="flex:1;text-align:center">
        <div style="font-size:26px;font-weight:700;color:#1e40af">{jobs_scraped}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px">Scraped</div>
      </div>
      <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0">
        <div style="font-size:26px;font-weight:700;color:#10b981">{jobs_matched}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px">Matched</div>
      </div>
      <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0">
        <div style="font-size:26px;font-weight:700;color:#f59e0b">{total_shown}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px">New (unapplied)</div>
      </div>
      <div style="flex:1;text-align:center;border-left:1px solid #e2e8f0">
        <div style="font-size:26px;font-weight:700;color:#6b7280">{len(applied_ids)}</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px">Already Applied</div>
      </div>
    </div>

    {sections_html}

    <!-- Footer -->
    <div style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;margin-top:16px">
      <div style="color:#94a3b8;font-size:11px">AI Job Hunter · Japesh Mohan · Auto-generated daily report</div>
    </div>

  </div>
</body>
</html>"""

    subject = f"🎯 {total_shown} New Job Matches — {date_str}"
    return send_email(subject, body)
