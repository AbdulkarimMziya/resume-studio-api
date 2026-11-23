import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    # Named api_client (not client) so it doesn't hide pytest-django's built-in `client` fixture.
    return APIClient()


FAKE_SUGGESTIONS = [
    {
        "original": "Helped with testing.",
        "replacement": "Wrote automated tests for API endpoints.",
        "reason": "The job asks for experience writing automated tests.",
    }
]


@pytest.fixture(autouse=True)
def fake_gemini(monkeypatch):
    # autouse=True: applies to EVERY test automatically, so no test can ever call the real,
    # paid Gemini API. Patch the name where it's USED (analysis.services), not where it's
    # defined (analysis.gemini): services.py imported get_suggestions into its own namespace.
    monkeypatch.setattr(
        "analysis.services.get_suggestions",
        lambda resume_text, job_description: FAKE_SUGGESTIONS,
    )
    return FAKE_SUGGESTIONS


@pytest.fixture(autouse=True)
def clear_throttle_counts():
    # Rate-limit counts live in the cache. Clear it so no test inherits another test's requests.
    cache.clear()
    yield
    cache.clear()
