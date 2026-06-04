from pathlib import Path
from datetime import datetime, timezone
from database.repository import get_top_matches, get_applications
from config.settings import EXPORTS_DIR


def generate_html_report(output_path: str = None) -> str:
    matches = get_top_matches(limit=50)
    applications = get_applications()

    # Normalise scores so the best job = 100%, others shown relative to it
    top_score = matches[0]['score'] if matches else 1
    rows = ""
    for job in matches:
        relative_pct = int((job['score'] / top_score) * 100)
        bar_color = "#10b981" if relative_pct >= 75 else "#3b82f6" if relative_pct >= 50 else "#f59e0b"
        city = job['city'] or job['location'] or '—'
        rows += f"""
        <tr>
          <td>{job['title']}</td>
          <td>{job['company'] or '—'}</td>
          <td>{city}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div style="background:#e2e8f0;border-radius:4px;width:80px;height:10px">
                <div style="background:{bar_color};width:{relative_pct}%;height:10px;border-radius:4px"></div>
              </div>
              <b style="color:{bar_color}">{relative_pct}%</b>
            </div>
          </td>
          <td><a href="{job['url']}" target="_blank">Apply</a></td>
        </tr>"""

    app_rows = ""
    status_colors = {
        "applied": "#3b82f6", "interview": "#f59e0b",
        "offer": "#10b981", "rejected": "#ef4444", "withdrawn": "#6b7280",
    }
    for app in applications:
        color = status_colors.get(app["status"], "#6b7280")
        app_rows += f"""
        <tr>
          <td>{app['title']}</td>
          <td>{app['company'] or '—'}</td>
          <td><span style="color:{color};font-weight:600">{app['status'].upper()}</span></td>
          <td>{app['applied_date'][:10]}</td>
          <td>{app['notes'] or '—'}</td>
        </tr>"""

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AI Job Hunter Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; color: #1e293b; }}
    h1 {{ color: #0f172a; }} h2 {{ color: #334155; margin-top: 2rem; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px;
             box-shadow: 0 1px 3px rgba(0,0,0,.1); overflow: hidden; }}
    th {{ background: #1e40af; color: white; padding: .75rem 1rem; text-align: left; }}
    td {{ padding: .65rem 1rem; border-bottom: 1px solid #e2e8f0; }}
    tr:last-child td {{ border-bottom: none; }}
    a {{ color: #2563eb; }}
    .meta {{ color: #64748b; font-size: .875rem; }}
  </style>
</head>
<body>
  <h1>AI Job Hunter</h1>
  <p class="meta">Generated: {generated} &nbsp;|&nbsp; {len(matches)} top matches &nbsp;|&nbsp; {len(applications)} applications tracked</p>

  <h2>Top Matches</h2>
  <table>
    <thead><tr><th>Title</th><th>Company</th><th>Location</th><th>Score</th><th>Link</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>Application Tracker</h2>
  <table>
    <thead><tr><th>Title</th><th>Company</th><th>Status</th><th>Applied</th><th>Notes</th></tr></thead>
    <tbody>{app_rows}</tbody>
  </table>
</body>
</html>"""

    out = Path(output_path or EXPORTS_DIR / "daily_report.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)
