import logging
from matching.resume_tailor import _call_llm

logger = logging.getLogger(__name__)


def generate_cover_letter(resume_text: str, job: dict) -> str:
    job_context = (
        f"Title: {job.get('title')}\n"
        f"Company: {job.get('company')}\n\n"
        f"Description:\n{job.get('description', '')[:3000]}"
    )
    prompt = (
        "You are an expert career coach. Write a concise, compelling cover letter (3 short paragraphs) "
        "for the candidate applying to this role. Be specific — reference the company name and role title. "
        "Do not fabricate experience the candidate doesn't have.\n\n"
        f"--- JOB ---\n{job_context}\n\n"
        f"--- RESUME ---\n{resume_text[:4000]}\n\n"
        "Write only the cover letter body (no subject line, no 'Dear Hiring Manager' header). "
        "Keep it under 250 words."
    )
    result = _call_llm(prompt)
    if not result:
        logger.warning("Cover letter generation returned empty result for job: %s", job.get("title"))
    return result
