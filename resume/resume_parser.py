try:
    import fitz
except ImportError as exc:
    raise ImportError(
        "PyMuPDF is required to extract resume text. Install it with: pip install PyMuPDF"
    ) from exc

from pathlib import Path

def extract_resume_text(pdf_path):
    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    doc.close()

    return text


if __name__ == "__main__":
    pdf = r"data/resumes/Resume_Japeshmohan.pdf"

    text = extract_resume_text(pdf)

    print(text[:3000])