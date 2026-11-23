import json

from google import genai
from google.genai import types

from pathlib import Path

from django.conf import settings

from .serializers import SuggestionSerializer
from .exceptions import AIBadOutput, AIUnavailable



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
    
    try:
        response = client.models.generate_content(
            model=settings.AI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=SCHEMA,
                max_output_tokens=2048,
            ),
        )
    except Exception as exc:                      # anything from the SDK or network: APIError, timeout...
        raise AIUnavailable() from exc

    try:
        data = json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as exc:   # not JSON, or no text at all (None)
        raise AIBadOutput() from exc

    shape = SuggestionSerializer(data=data.get("suggestions"), many=True)
    if not shape.is_valid():
        raise AIBadOutput()

    return shape.validated_data
