# resume/profile_builder.py

from resume.resume_parser import extract_resume_text
from resume.skill_extractor import extract_skills

def build_profile():

    text = extract_resume_text(
        "data/resumes/Resume_Japeshmohan.pdf"
    )

    skills = extract_skills(text)
    skills.extend([
    "software engineer",
    "software developer",
    "backend engineer",
    "backend developer",
    "full stack developer",
    "python developer",
    "machine learning",
    "artificial intelligence"
])

    skills = list(set(skills))

    profile = {
        "skills": skills,
        "titles": [
            # Software / Backend
            "software engineer",
            "software developer",
            "backend engineer",
            "backend developer",
            "full stack developer",
            "full stack engineer",
            "python developer",
            "python engineer",
            # AI / ML / Data
            "machine learning engineer",
            "ai engineer",
            "computer vision engineer",
            "data engineer",
            "data scientist",
            "data analyst",
            # QA / Testing
            "qa engineer",
            "quality assurance engineer",
            "test engineer",
            "automation engineer",
            "sdet",
            "qa analyst",
            "software tester",
            "manual tester",
        ],
        "locations": [
            "hyderabad",
            "bangalore",
            "remote"
        ]
    }

    return profile


if __name__ == "__main__":

    profile = build_profile()

    print(profile)