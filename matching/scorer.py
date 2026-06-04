import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
from config.settings import MIN_MATCH_SCORE

logger = logging.getLogger(__name__)

_resume_text_cache: str | None = None
_resume_skills_cache: list[str] | None = None

_EXTRA_STOP_WORDS = [
    "university", "institute", "college", "cgpa", "gpa", "btech",
    "coursework", "semester", "course", "degree", "education", "graduation",
    "dsa", "algorithms", "dbms",
    "linkedin", "github", "gmail", "phone", "email", "resume", "cv",
]

# Synonyms: if resume has key, also check these in job description
_SKILL_SYNONYMS = {
    "python":           ["python", "django", "flask", "fastapi"],
    "machine learning": ["machine learning", "ml", "deep learning", "ai", "artificial intelligence"],
    "javascript":       ["javascript", "js", "typescript", "ts", "node", "react", "vue", "angular"],
    "sql":              ["sql", "mysql", "postgresql", "postgres", "sqlite", "database", "rdbms"],
    "opencv":           ["opencv", "computer vision", "cv", "image processing", "object detection"],
    "pytorch":          ["pytorch", "torch", "tensorflow", "keras", "neural network"],
    "scikit-learn":     ["scikit", "sklearn", "scikit-learn", "machine learning"],
    "react":            ["react", "reactjs", "frontend", "front-end", "ui"],
    "docker":           ["docker", "kubernetes", "k8s", "containerization", "devops"],
    "selenium":         ["selenium", "automation testing", "ui testing", "webdriver"],
    "pytest":           ["pytest", "unit testing", "testing", "test automation", "qa"],
    "postman":          ["postman", "api testing", "rest api", "api"],
    "git":              ["git", "github", "gitlab", "version control"],
    "fastapi":          ["fastapi", "flask", "django", "rest api", "backend", "api"],
    "mongodb":          ["mongodb", "nosql", "document database"],
    "yolov8":           ["yolo", "yolov8", "object detection", "computer vision"],
    "node.js":          ["node", "nodejs", "express", "backend", "server"],
    "java":             ["java", "spring", "springboot"],
    "c++":              ["c++", "cpp", "systems programming"],
    "rest api":         ["rest", "api", "restful", "web services", "http"],
    "manual testing":   ["manual testing", "test cases", "functional testing", "qa", "quality assurance"],
    "api testing":      ["api testing", "postman", "rest api", "integration testing"],
}


def _get_resume_text() -> str:
    global _resume_text_cache
    if _resume_text_cache is None:
        from resume.resume_parser import extract_resume_text
        from config.settings import RESUME_DIR
        pdf_files = list(RESUME_DIR.glob("*.pdf"))
        if not pdf_files:
            logger.error("No PDF resume found in %s — all jobs will score 0", RESUME_DIR)
            _resume_text_cache = ""
            return _resume_text_cache
        raw = extract_resume_text(str(pdf_files[0]))
        edu_cut = re.search(
            r"\b(experience|projects|skills|work history|internship|achievements)\b",
            raw, re.IGNORECASE
        )
        # Use from first non-education section; fall back to full text if not found
        _resume_text_cache = raw[edu_cut.start():] if edu_cut else raw
        if not _resume_text_cache.strip():
            _resume_text_cache = raw
    return _resume_text_cache


def _get_resume_skills() -> list[str]:
    global _resume_skills_cache
    if _resume_skills_cache is None:
        from resume.skill_extractor import extract_skills
        _resume_skills_cache = extract_skills(_get_resume_text())
    return _resume_skills_cache


def _tfidf_score(resume_text: str, job_description: str) -> float:
    if not job_description or not resume_text:
        return 0.0
    stop_words = list(ENGLISH_STOP_WORDS) + _EXTRA_STOP_WORDS
    vectorizer = TfidfVectorizer(
        stop_words=stop_words,
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )
    try:
        tfidf = vectorizer.fit_transform([resume_text, job_description])
        return round(float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]), 4)
    except Exception as exc:
        logger.warning("TF-IDF failed: %s", exc)
        return 0.0


def _skill_overlap_score(resume_skills: list[str], job_description: str) -> float:
    """
    For each resume skill, check if it OR any of its synonyms appear in the job description.
    Returns fraction of resume skills that have at least one match.
    """
    if not resume_skills or not job_description:
        return 0.0
    desc_lower = job_description.lower()
    hits = 0
    for skill in resume_skills:
        # Check skill itself
        if skill.lower() in desc_lower:
            hits += 1
            continue
        # Check synonyms
        synonyms = _SKILL_SYNONYMS.get(skill.lower(), [])
        if any(syn in desc_lower for syn in synonyms):
            hits += 1
    return round(hits / len(resume_skills), 4)


def ats_score(resume_text: str, job_description: str) -> float:
    """Combined ATS score: 60% TF-IDF cosine + 40% skill overlap with synonyms."""
    resume_skills = _get_resume_skills()
    tfidf = _tfidf_score(resume_text, job_description)
    overlap = _skill_overlap_score(resume_skills, job_description)
    return round(0.60 * tfidf + 0.40 * overlap, 4)


def score_job(job: dict, resume_text: str) -> float:
    return ats_score(resume_text, job.get("description") or "")


def filter_jobs(jobs: list[dict], profile: dict = None, min_score: float = None) -> list[dict]:
    """
    Score all jobs using combined TF-IDF + skill overlap (with synonyms).
    Dedupes by title+company. Returns matches above threshold sorted best-first.
    """
    threshold = min_score if min_score is not None else MIN_MATCH_SCORE
    resume_text = _get_resume_text()

    # Dedupe by title+company; fall back to job id if both empty
    seen: set[str] = set()
    unique_jobs = []
    for job in jobs:
        title   = (job.get("title")   or "").lower().strip()
        company = (job.get("company") or "").lower().strip()
        key = f"{title}|{company}" if (title or company) else job.get("id", "")
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    scored = []
    for job in unique_jobs:
        s = score_job(job, resume_text)
        # Companies (careers) source: pre-filtered at scrape time, no score threshold
        job_threshold = 0.0 if job.get("source") == "careers" else threshold
        if s >= job_threshold:
            scored.append({**job, "_score": s})

    scored.sort(key=lambda x: x["_score"], reverse=True)

    logger.info(
        "%d / %d unique jobs passed ATS threshold %.2f (deduped from %d total)",
        len(scored), len(unique_jobs), threshold, len(jobs),
    )
    return scored
