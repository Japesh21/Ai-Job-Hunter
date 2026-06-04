import csv
from pathlib import Path
from database.repository import get_top_matches, get_applications
from config.settings import EXPORTS_DIR


def export_matches_csv(output_path: str = None) -> str:
    rows = get_top_matches(limit=200)
    out = Path(output_path or EXPORTS_DIR / "matched_jobs.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "company", "location", "score", "url", "posted_at", "matched_at"])
        for r in rows:
            writer.writerow([r["title"], r["company"], r["location"],
                              f"{r['score']:.2f}", r["url"], r["posted_at"], r["matched_at"]])
    return str(out)


def export_applications_csv(output_path: str = None) -> str:
    rows = get_applications()
    out = Path(output_path or EXPORTS_DIR / "applications.csv")
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "company", "status", "applied_date", "url", "notes"])
        for r in rows:
            writer.writerow([r["title"], r["company"], r["status"],
                              r["applied_date"], r["url"], r["notes"]])
    return str(out)
