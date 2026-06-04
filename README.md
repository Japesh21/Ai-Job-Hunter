# AI Job Hunter 🎯

An automated fresher job hunting system for India. Scrapes multiple job boards daily, scores listings against your resume using TF-IDF + skill matching, and delivers ranked results through a Streamlit dashboard and daily email report.

Built by **Japesh Mohan** — fresher targeting AI/ML, Data Engineering, Web Dev, and QA roles across India.

---

## What it does

- Scrapes **4 sources** every day: Adzuna API, Internshala, JSearch (LinkedIn/Indeed/Glassdoor), and 800 company career pages
- Filters to **fresher/0-2 years, onsite India only** — blocks senior roles, WFH, closed jobs, spam
- Scores every job against your resume using **TF-IDF + skill overlap**
- Shows results in a **Streamlit dashboard** with filters by source, type, city, match %
- Tracks applications: mark applied → interview → offer → rejected
- Sends a **daily email report** with top matches

---

## Sources

| Source | Method | Jobs/run |
|--------|--------|----------|
| Adzuna | Official API | ~80 |
| Internshala | Web scrape (BeautifulSoup) | ~440 |
| JSearch | RapidAPI (LinkedIn + Indeed + Glassdoor) | ~170 |
| Company career pages | Playwright (800 companies CSV) | ~10-15 |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/ai-job-hunter.git
cd ai-job-hunter

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Set up environment variables
copy .env.example .env
# Edit .env with your API keys

# 5. Add your resume
# Place your PDF resume in: data/resumes/YourName.pdf

# 6. Run
python main.py all
```

---

## Configuration

### Required API Keys (`.env`)

```env
# Job board APIs
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
JSEARCH_API_KEY=your_rapidapi_key     # Free tier: rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

# Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_app_password           # Gmail App Password (not your real password)
NOTIFY_EMAIL=where_to_send@gmail.com
```

### Filters (all configurable)

| Filter | Default | Where |
|--------|---------|-------|
| Score threshold | 0.08 | `config/settings.py` |
| Max job age | 30 days | `scrapers/*/scraper.py` |
| Min salary (internship) | ₹15,000/month | `scrapers/internshala/scraper.py` |
| Min salary (full-time) | ₹30,000/month | `scrapers/internshala/scraper.py` |
| Companies per run | 50 of 800 | `config/settings.py` |
| Blocked keywords/companies | see file | `config/blacklist.json` |

### Company career pages

Add or update companies in `config/companies.csv`:
```csv
Company_Name,Career_Page
Infosys,https://career.infosys.com
Google,https://careers.google.com
```

---

## Commands

```bash
python main.py scrape          # Scrape all sources
python main.py match           # Score jobs against resume
python main.py report          # Generate HTML + CSV report
python main.py email           # Send daily email report
python main.py all             # scrape + match + report + email
python main.py scrape-retry    # Retry failed career page companies
python main.py schedule        # Run automatically at 8 AM daily
```

---

## Dashboard

```bash
.\venv\Scripts\streamlit run dashboard\app.py
# Open: http://localhost:8501
```

**Features:**
- Filter by source: All / Adzuna / Internshala / JSearch / Companies
- Filter by type: All / Internship / Job
- Filter by city, search by title/company, minimum match %
- Mark jobs as Applied — they disappear from the main list
- Update application status: applied → interview → offer / rejected
- Undo applied (puts job back in main list)
- Block a company permanently from the sidebar
- Run scrape + match + email without touching the terminal

---

## Project Structure

```
ai-job-hunter/
├── config/
│   ├── settings.py          # All configurable settings
│   ├── blacklist.json       # Blocked keywords and companies
│   └── companies.csv        # 800 company career page URLs
│
├── scrapers/
│   ├── adzuna/              # Adzuna API scraper
│   ├── internshala/         # Internshala web scraper
│   ├── jsearch/             # JSearch RapidAPI scraper
│   └── careers/             # Playwright career page scraper
│
├── matching/
│   └── scorer.py            # TF-IDF + skill overlap scoring
│
├── database/
│   ├── models.py            # SQLite schema
│   ├── connection.py        # DB connection
│   └── repository.py       # CRUD operations
│
├── dashboard/
│   └── app.py               # Streamlit web dashboard
│
├── notifications/
│   └── email_sender.py      # Daily email report
│
├── resume/
│   ├── resume_parser.py     # PDF → text (PyMuPDF)
│   └── skill_extractor.py   # Extract skills from resume
│
├── reports/
│   ├── html_report.py       # HTML report generator
│   └── csv_exporter.py      # CSV export
│
├── scheduler/
│   └── scheduler.py         # Daily 8 AM auto-run
│
├── data/
│   ├── jobs.db              # SQLite database (gitignored)
│   └── resumes/             # Your PDF resume (gitignored)
│
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
└── Makefile
```

---

## Tech Stack

- **Python 3.10+**
- **Playwright** — headless Chromium for career page scraping
- **BeautifulSoup** — Internshala scraping
- **scikit-learn** — TF-IDF scoring
- **SQLite** — local job database
- **Streamlit** — dashboard
- **PyMuPDF** — resume PDF parsing
- **schedule** — daily automation

---

## How scoring works

Each job is scored against your resume using:
- **60% TF-IDF cosine similarity** — word frequency matching between resume and job description
- **40% skill overlap** — checks how many of your skills appear in the job description, with synonyms (e.g. "opencv" also matches "computer vision")

Score threshold: 0.08 for Adzuna/Internshala/JSearch. Career page jobs bypass the threshold (pre-filtered at scrape time).

---

## License

MIT
