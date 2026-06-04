import pytest
from matching.scorer import _tfidf_score, _skill_overlap_score, ats_score, filter_jobs

RESUME_TEXT = (
    "Projects: Built a computer vision system using Python, OpenCV, YOLOv8 for object detection. "
    "Developed a FastAPI backend with MongoDB. Used PyTorch for model training. "
    "Skills: Python, JavaScript, React, SQL, Docker, Git, pytest, selenium."
)

GOOD_JOB = {
    "id": "job1",
    "title": "Junior Data Scientist",
    "company": "TechCorp",
    "location": "Bangalore",
    "city": "Bangalore",
    "description": (
        "We are looking for a fresher or junior data scientist with Python, machine learning, "
        "and SQL skills. Experience with PyTorch or scikit-learn is a plus. "
        "0-2 years experience. Will work on computer vision and NLP projects."
    ),
    "url": "https://example.com/job/1",
}

BAD_JOB = {
    "id": "job2",
    "title": "Plumber Technician",
    "company": "Pipes Inc",
    "location": "Mumbai",
    "city": "Mumbai",
    "description": "Fix pipes and drainage systems. No tech skills required. Physical work only.",
    "url": "https://example.com/job/2",
}

QA_JOB = {
    "id": "job3",
    "title": "QA Engineer Fresher",
    "company": "Startup Ltd",
    "location": "Hyderabad",
    "city": "Hyderabad",
    "description": (
        "Looking for a fresher QA engineer. Should know selenium, pytest, manual testing, "
        "bug tracking, and API testing. Python knowledge is a plus. 0-1 years experience."
    ),
    "url": "https://example.com/job/3",
}


def test_tfidf_good_job_scores_higher_than_bad():
    good = _tfidf_score(RESUME_TEXT, GOOD_JOB["description"])
    bad = _tfidf_score(RESUME_TEXT, BAD_JOB["description"])
    assert good > bad, f"Expected good ({good}) > bad ({bad})"


def test_tfidf_score_in_range():
    score = _tfidf_score(RESUME_TEXT, GOOD_JOB["description"])
    assert 0.0 <= score <= 1.0


def test_tfidf_empty_description_returns_zero():
    assert _tfidf_score(RESUME_TEXT, "") == 0.0
    assert _tfidf_score("", GOOD_JOB["description"]) == 0.0


def test_skill_overlap_finds_matching_skills():
    skills = ["python", "pytorch", "opencv"]
    score = _skill_overlap_score(skills, GOOD_JOB["description"])
    assert score > 0.0, f"Expected > 0.0, got {score}"


def test_skill_overlap_no_match():
    skills = ["python", "pytorch", "opencv"]
    score = _skill_overlap_score(skills, BAD_JOB["description"])
    assert score == 0.0


def test_skill_overlap_empty_inputs():
    assert _skill_overlap_score([], GOOD_JOB["description"]) == 0.0
    assert _skill_overlap_score(["python"], "") == 0.0


def test_ats_score_qa_job():
    score = ats_score(RESUME_TEXT, QA_JOB["description"])
    assert score > 0.0, f"QA job should score > 0, got {score}"


def test_filter_jobs_dedupes():
    duplicate = {**GOOD_JOB, "id": "job1b", "city": "Delhi"}
    jobs = [GOOD_JOB, BAD_JOB, duplicate]
    results = filter_jobs(jobs, min_score=0.0)
    titles_companies = [(r["title"], r["company"]) for r in results]
    assert len(titles_companies) == len(set(titles_companies)), "Duplicates found after filter"


def test_filter_jobs_sorts_descending():
    jobs = [GOOD_JOB, BAD_JOB, QA_JOB]
    results = filter_jobs(jobs, min_score=0.0)
    scores = [r["_score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Results not sorted by score descending"
