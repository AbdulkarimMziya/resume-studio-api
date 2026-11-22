import json

from google import genai
from google.genai import types

from pathlib import Path

from django.conf import settings

from .serializers import SuggestionSerializer



SCHEMA = { 
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original":{"type": "string"},
                    "replacement": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["original", "replacement", "reason"]
            }
        }
    },
    "required": ["suggestions"]
}


PROMPT_TEMPLATE = (Path(__file__).parent / "prompt.txt").read_text()

def build_prompt(resume_text, job_description):
    return PROMPT_TEMPLATE.format(resume_text=resume_text, job_description=job_description)



def get_suggestions(resume_text, job_description):
    prompt = build_prompt(resume_text, job_description)
    client = genai.Client(api_key=settings.AI_API_KEY, http_options=types.HttpOptions(timeout=30_000))
    
    response = client.models.generate_content(
        model=settings.AI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=SCHEMA,
            max_output_tokens=2048,
        ),
    )

    data = json.loads(response.text)
    
    shape = SuggestionSerializer(data=data["suggestions"], many=True)
    if not shape.is_valid():
        raise ValueError(f"Gemini returned an invalid shape: {shape.errors}")
    return shape.validated_data
