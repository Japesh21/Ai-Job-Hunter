import sys
import os
import json
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from database.connection import init_db
from database.repository import (
    get_top_matches, get_applications, add_application,
    update_application_status, delete_application,
)

st.set_page_config(
    page_title="AI Job Hunter — Japesh",
    page_icon="🎯",
    layout="wide",
)

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

def time_ago(iso_str: str) -> str:
    """Convert ISO datetime string to '3 days ago' style."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - dt).days
        if days == 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        if days < 7:
            return f"{days} days ago"
        if days < 30:
            return f"{days // 7}w ago"
        return f"{days // 30}mo ago"
    except Exception:
        return iso_str[:10] if iso_str else "—"


def match_bar(pct: int) -> str:
    color = "#10b981" if pct >= 70 else "#3b82f6" if pct >= 40 else "#f59e0b"
    return (
        f"<div style='display:flex;align-items:center;gap:8px'>"
        f"<div style='background:#e2e8f0;border-radius:6px;width:100px;height:12px'>"
        f"<div style='background:{color};width:{pct}%;height:12px;border-radius:6px'></div></div>"
        f"<b style='color:{color}'>{pct}%</b></div>"
    )


def source_badge(source: str) -> str:
    if source == "adzuna":
        return "<span style='background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600'>🔵 Adzuna</span>"
    if source == "internshala":
        return "<span style='background:#ffedd5;color:#c2410c;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600'>🟠 Internshala</span>"
    if source == "jsearch":
        return "<span style='background:#f0fdf4;color:#166534;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600'>🟢 JSearch</span>"
    if source == "careers":
        return "<span style='background:#fdf4ff;color:#7e22ce;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600'>🏢 Company</span>"
    return ""


def type_badge(job_type: str) -> str:
    if job_type == "internship":
        return "<span style='background:#f0fdf4;color:#15803d;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600'>🎓 Internship</span>"
    if job_type == "job":
        return "<span style='background:#faf5ff;color:#7e22ce;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600'>💼 Job</span>"
    return ""


STATUS_OPTIONS = ["applied", "interview", "offer", "rejected", "withdrawn"]
STATUS_COLORS  = {
    "applied":   ("#3b82f6", "🔵"),
    "interview": ("#f59e0b", "🟡"),
    "offer":     ("#10b981", "🟢"),
    "rejected":  ("#ef4444", "🔴"),
    "withdrawn": ("#6b7280", "⚪"),
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🎯 AI Job Hunter")
    st.caption("Japesh Mohan · Fresher")
    st.divider()
    page = st.radio("Navigate", ["🔍 Job Matches", "📋 Applied Jobs", "📊 Stats"])
    st.divider()

    if st.button("🔄 Refresh data", use_container_width=True):
        st.rerun()

    if st.button("▶ Run scrape + match", use_container_width=True):
        import subprocess
        with st.spinner("Scraping & matching jobs... (2–3 min)"):
            result = subprocess.run(
                [sys.executable, "main.py", "all"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
        if result.returncode == 0:
            st.success("Done! Data updated.")
            st.rerun()
        else:
            st.error("Pipeline error:")
            st.code(result.stderr[-800:] if result.stderr else result.stdout[-800:])

    if st.button("📧 Send report email", use_container_width=True):
        import subprocess
        with st.spinner("Sending email..."):
            result = subprocess.run(
                [sys.executable, "main.py", "email"],
                capture_output=True, text=True, cwd=PROJECT_ROOT,
            )
        if result.returncode == 0:
            st.success("Email sent to japeshmohan@gmail.com!")
        else:
            st.error("Email failed:")
            st.code(result.stderr[-400:] if result.stderr else result.stdout[-400:])

    st.divider()
    st.markdown("**🚫 Block a company**")
    block_company = st.text_input(
        "Company name", placeholder="e.g. SpamAgency Pvt Ltd",
        label_visibility="collapsed",
    )
    if st.button("Block permanently", use_container_width=True) and block_company.strip():
        bl_path = os.path.join(PROJECT_ROOT, "config", "blacklist.json")
        with open(bl_path, "r", encoding="utf-8") as f:
            bl = json.load(f)
        name = block_company.strip()
        if name not in bl["blocked_companies"]:
            bl["blocked_companies"].append(name)
            with open(bl_path, "w", encoding="utf-8") as f:
                json.dump(bl, f, indent=2)
            st.success(f"'{name}' blocked.")
        else:
            st.info(f"'{name}' is already blocked.")

# ── Load data ─────────────────────────────────────────────────────────────────
_raw_matches = [dict(j) for j in get_top_matches(limit=500)]
_seen: set = set()
all_matches: list = []
for j in _raw_matches:
    if j["id"] not in _seen:
        _seen.add(j["id"])
        all_matches.append(j)

all_apps    = [dict(a) for a in get_applications()]
applied_ids = {a["job_id"] for a in all_apps}

top_score = all_matches[0]["score"] if all_matches else 1.0
if top_score == 0:
    top_score = 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# Page: Job Matches
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🔍 Job Matches":
    new_jobs = [j for j in all_matches if j["id"] not in applied_ids]

    st.header("🔍 Job Matches")
    st.caption(
        f"**{len(new_jobs)}** new &nbsp;·&nbsp; "
        f"**{len(applied_ids)}** applied &nbsp;·&nbsp; sorted by match score"
    )

    if not all_matches:
        st.warning("No jobs yet. Click **▶ Run scrape + match** in the sidebar.")
    else:
        # ── Filters ──────────────────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)
        with c1:
            search = st.text_input("🔎 Search title / company", placeholder="e.g. Python, QA...")
        with c2:
            cities = sorted({j.get("city") or "Unknown" for j in new_jobs})
            city_filter = st.multiselect("📍 City", cities)
        with c3:
            min_pct = st.slider("Min match %", 0, 100, 0, step=5)

        c4, c5 = st.columns(2)
        with c4:
            st.caption("📡 **Source**")
            source_filter = st.radio(
                "Source", ["All", "Adzuna", "Internshala", "JSearch", "Companies"],
                horizontal=True, label_visibility="collapsed",
            )
        with c5:
            st.caption("💼 **Type**")
            type_filter = st.radio(
                "Type", ["All", "Internship", "Job"],
                horizontal=True, label_visibility="collapsed",
            )

        # Source label → DB value mapping
        SOURCE_MAP = {"Adzuna": "adzuna", "Internshala": "internshala", "JSearch": "jsearch", "Companies": "careers"}

        # ── Apply filters ────────────────────────────────────────────────────
        filtered = new_jobs
        if search:
            q = search.lower()
            filtered = [j for j in filtered if q in (j.get("title") or "").lower()
                        or q in (j.get("company") or "").lower()]
        if city_filter:
            filtered = [j for j in filtered if (j.get("city") or "Unknown") in city_filter]
        if min_pct > 0:
            filtered = [j for j in filtered if int((j["score"] / top_score) * 100) >= min_pct]
        if source_filter != "All":
            filtered = [j for j in filtered if j.get("source") == SOURCE_MAP.get(source_filter)]
        if type_filter == "Internship":
            filtered = [j for j in filtered if j.get("job_type") == "internship"]
        elif type_filter == "Job":
            filtered = [j for j in filtered if j.get("job_type") == "job"]

        st.caption(f"Showing **{len(filtered)}** jobs")
        st.divider()

        if not filtered:
            st.info("No jobs match your filters.")
        else:
            for job in filtered:
                pct    = int((job["score"] / top_score) * 100)
                src    = source_badge(job.get("source") or "")
                typ    = type_badge(job.get("job_type") or "")
                posted = time_ago(job.get("posted_at") or "")
                city   = job.get("city") or job.get("location") or "—"

                with st.container(border=True):
                    c1, c2, c3 = st.columns([5, 2, 1])

                    with c1:
                        st.markdown(f"### {job['title']}")
                        st.markdown(
                            f"🏢 **{job.get('company') or '—'}** &nbsp;|&nbsp; "
                            f"📍 {city} &nbsp;|&nbsp; 🕒 {posted}",
                        )
                        # Source + type badges
                        badges = " &nbsp; ".join(b for b in [src, typ] if b)
                        if badges:
                            st.markdown(badges, unsafe_allow_html=True)
                        st.markdown(match_bar(pct), unsafe_allow_html=True)

                        desc = (job.get("description") or "")
                        with st.expander("View description"):
                            st.write(desc[:600] + ("…" if len(desc) > 600 else ""))

                    with c2:
                        sal_min = job.get("salary_min")
                        sal_max = job.get("salary_max")
                        if sal_min and sal_max:
                            st.markdown(f"💰 ₹{int(sal_min):,} – ₹{int(sal_max):,}")
                        elif sal_min:
                            st.markdown(f"💰 ₹{int(sal_min):,}+")
                        else:
                            st.markdown("💰 Not listed")
                        if job.get("url"):
                            st.link_button("🌐 Open job", job["url"], use_container_width=True)

                    with c3:
                        if st.button("✅ Mark Applied", key=f"apply_{job['id']}",
                                     use_container_width=True, type="primary"):
                            add_application(job["id"])
                            st.success("Logged!")
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# Page: Applied Jobs
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Applied Jobs":
    st.header("📋 Applied Jobs")
    st.caption(f"**{len(all_apps)}** applications tracked")

    if not all_apps:
        st.info("No applications yet. Go to Job Matches and click ✅ Mark Applied.")
    else:
        status_filter = st.selectbox("Filter by status", ["All"] + STATUS_OPTIONS)
        shown = (
            all_apps if status_filter == "All"
            else [a for a in all_apps if a["status"] == status_filter]
        )

        if not shown:
            st.info(f"No applications with status '{status_filter}'.")

        for app in shown:
            color, emoji = STATUS_COLORS.get(app["status"], ("#6b7280", "⚪"))
            with st.container(border=True):
                c1, c2, c3 = st.columns([5, 2, 2])

                with c1:
                    st.markdown(f"### {app['title']}")
                    city    = app.get("city") or app.get("location") or "—"
                    company = app.get("company") or "—"
                    applied = time_ago(app.get("applied_date") or "")
                    posted  = time_ago(app.get("job_posted_at") or "")
                    st.markdown(
                        f"🏢 **{company}** &nbsp;|&nbsp; 📍 {city} &nbsp;|&nbsp; "
                        f"Applied: {applied}"
                    )
                    # Source + type badges
                    src = source_badge(app.get("source") or "")
                    typ = type_badge(app.get("job_type") or "")
                    badges = " &nbsp; ".join(b for b in [src, typ] if b)
                    if badges:
                        st.markdown(badges, unsafe_allow_html=True)

                    sal = app.get("salary_min")
                    if sal:
                        st.caption(f"💰 ₹{int(sal):,}/mo &nbsp;|&nbsp; Job posted: {posted}")
                    if app.get("notes"):
                        st.caption(f"📝 {app['notes']}")

                with c2:
                    st.markdown(
                        f"<span style='color:{color};font-size:1.1rem;font-weight:700'>"
                        f"{emoji} {app['status'].upper()}</span>",
                        unsafe_allow_html=True,
                    )
                    if app.get("url"):
                        st.link_button("🌐 View job", app["url"], use_container_width=True)

                with c3:
                    cur_idx = STATUS_OPTIONS.index(app["status"]) if app["status"] in STATUS_OPTIONS else 0
                    new_status = st.selectbox(
                        "Update status", STATUS_OPTIONS, index=cur_idx,
                        key=f"status_{app['id']}",
                    )
                    notes = st.text_input(
                        "Notes", value=app.get("notes") or "",
                        key=f"notes_{app['id']}", placeholder="e.g. HR called...",
                    )
                    if st.button("💾 Save", key=f"save_{app['id']}", use_container_width=True):
                        update_application_status(app["id"], new_status, notes or None)
                        st.success("Saved!")
                        st.rerun()
                    if st.button("↩ Undo (remove)", key=f"undo_{app['id']}",
                                 use_container_width=True,
                                 help="Job goes back to Job Matches"):
                        delete_application(app["id"])
                        st.success(f"'{app['title']}' is back in Job Matches.")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# Page: Stats
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Stats":
    import pandas as pd

    st.header("📊 Stats")

    total_matched = len(all_matches)
    total_applied = len(all_apps)
    interviews    = sum(1 for a in all_apps if a["status"] == "interview")
    offers        = sum(1 for a in all_apps if a["status"] == "offer")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total matches", total_matched)
    c2.metric("Applied", total_applied)
    c3.metric("Interviews", interviews)
    c4.metric("Offers 🎉", offers)

    st.divider()

    # ── All matched jobs breakdown (always shown) ─────────────────────────────
    st.subheader("All matched jobs breakdown")
    col1, col2 = st.columns(2)

    SOURCE_LABELS = {"adzuna": "Adzuna", "internshala": "Internshala", "jsearch": "JSearch", "careers": "Companies"}

    with col1:
        st.markdown("**By source**")
        src_counts = {}
        for j in all_matches:
            s = SOURCE_LABELS.get(j.get("source") or "", "Unknown")
            src_counts[s] = src_counts.get(s, 0) + 1
        if src_counts:
            df_src = pd.DataFrame(src_counts.items(), columns=["Source", "Jobs"])
            st.bar_chart(df_src.set_index("Source"))

    with col2:
        st.markdown("**By type**")
        type_counts = {}
        for j in all_matches:
            t = j.get("job_type") or "unknown"
            label = {"internship": "Internship", "job": "Full-time Job"}.get(t, "Unknown")
            type_counts[label] = type_counts.get(label, 0) + 1
        if type_counts:
            df_type = pd.DataFrame(type_counts.items(), columns=["Type", "Jobs"])
            st.bar_chart(df_type.set_index("Type"))

    # Match score distribution
    if all_matches:
        st.subheader("Match score distribution")
        scores = [int((j["score"] / top_score) * 100) for j in all_matches]
        df_scores = pd.DataFrame({"Match %": scores})
        st.bar_chart(df_scores["Match %"].value_counts().sort_index())

    st.divider()

    # ── Application stats (shown only when applications exist) ────────────────
    if not all_apps:
        st.info("Apply to some jobs to see application stats here.")
    else:
        st.subheader("Application stats")
        col3, col4 = st.columns(2)

        with col3:
            st.markdown("**Status breakdown**")
            status_counts = {}
            for a in all_apps:
                status_counts[a["status"]] = status_counts.get(a["status"], 0) + 1
            df_s = pd.DataFrame(status_counts.items(), columns=["Status", "Count"])
            st.bar_chart(df_s.set_index("Status"))

        with col4:
            st.markdown("**Top companies applied to**")
            co_counts = {}
            for a in all_apps:
                co = a.get("company") or "Unknown"
                co_counts[co] = co_counts.get(co, 0) + 1
            df_co = (
                pd.DataFrame(co_counts.items(), columns=["Company", "Count"])
                .sort_values("Count", ascending=False)
                .head(10)
            )
            st.bar_chart(df_co.set_index("Company"))

        # Source breakdown for applied jobs
        col5, col6 = st.columns(2)
        with col5:
            st.markdown("**Applied — by source**")
            app_src = {}
            for a in all_apps:
                s = SOURCE_LABELS.get(a.get("source") or "", "Unknown")
                app_src[s] = app_src.get(s, 0) + 1
            if app_src:
                df_as = pd.DataFrame(app_src.items(), columns=["Source", "Count"])
                st.bar_chart(df_as.set_index("Source"))

        with col6:
            st.markdown("**Applied — by type**")
            app_type = {}
            for a in all_apps:
                t = a.get("job_type") or "unknown"
                label = {"internship": "Internship", "job": "Full-time Job"}.get(t, "Unknown")
                app_type[label] = app_type.get(label, 0) + 1
            if app_type:
                df_at = pd.DataFrame(app_type.items(), columns=["Type", "Count"])
                st.bar_chart(df_at.set_index("Type"))
