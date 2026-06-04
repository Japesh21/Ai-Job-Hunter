# resume/skill_extractor.py

KNOWN_SKILLS = [
    # Core languages
    "python", "c++", "c", "javascript", "java", "sql",
    # Databases
    "mongodb", "mysql", "postgresql",
    # Web / Frontend
    "react", "node.js", "express.js", "html", "css",
    # AI / ML / CV
    "pytorch", "scikit-learn", "pandas", "numpy",
    "opencv", "yolov8", "machine learning", "deep learning",
    "computer vision", "nlp", "tensorflow",
    # Backend / DevOps
    "docker", "fastapi", "git", "flask", "django", "rest api",
    # Real-time
    "webrtc", "socket.io",
    # QA / Testing
    "pytest", "selenium", "unittest", "postman",
    "jira", "jenkins", "manual testing", "api testing",
    "test cases", "bug tracking", "automation testing",
]

def extract_skills(text):
    text = text.lower()

    skills = []

    for skill in KNOWN_SKILLS:
        if skill.lower() in text:
            skills.append(skill)

    return sorted(list(set(skills)))