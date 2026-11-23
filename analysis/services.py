from .gemini import get_suggestions
from .exceptions import AIBadOutput

def _normalise(text):
    return " ".join(text.split())


def analyze_resume(resume_text, job_description):
    suggestions = get_suggestions(resume_text, job_description)   # a list: [{...}, {...}]

    resume = _normalise(resume_text)
    for suggestion in suggestions:
        if _normalise(suggestion["original"]) not in resume:
            raise AIBadOutput()
        
    return {"suggestions": suggestions}