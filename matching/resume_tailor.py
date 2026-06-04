import logging
import os
from config.settings import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def tailor_resume(resume_text: str, job: dict) -> str:
    """Return a tailored resume summary paragraph for the given job."""
    prompt = _build_prompt(resume_text, job, mode="resume")
    return _call_llm(prompt)


def _build_prompt(resume_text: str, job: dict, mode: str) -> str:
    job_context = f"Title: {job.get('title')}\nCompany: {job.get('company')}\n\nDescription:\n{job.get('description', '')[:3000]}"
    if mode == "resume":
        return (
            "You are a professional resume writer. Given the candidate's resume and a job posting, "
            "rewrite the professional summary section (3-4 sentences) to best match this specific role. "
            "Keep it honest — only emphasise skills the candidate actually has.\n\n"
            f"--- JOB ---\n{job_context}\n\n--- RESUME ---\n{resume_text[:4000]}\n\n"
            "Write only the tailored summary, no preamble."
        )
    return ""


def _call_llm(prompt: str) -> str:
    if ANTHROPIC_API_KEY:
        return _call_anthropic(prompt)
    if OPENAI_API_KEY:
        return _call_openai(prompt)
    logger.warning("No LLM API key configured — returning empty tailored text")
    return ""


def _call_anthropic(prompt: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.error("Anthropic call failed: %s", exc)
        return ""


def _call_openai(prompt: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("OpenAI call failed: %s", exc)
        return ""
