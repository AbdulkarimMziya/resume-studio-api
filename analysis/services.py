from .gemini import get_suggestions
def analyze_resume(resume_text, job_description):
    suggestions = get_suggestions(resume_text, job_description)   # a list: [{...}, {...}]
    return {"suggestions": suggestions}