import pytest

from analysis.exceptions import AIBadOutput, AIUnavailable



# What to test:
# 1. a valid request → 200 plus the response shape;
# 2. a blank and a missing value for each field;
# 3. over-length text for each field;
# 4. GET → 405;
# 5. the schema lists /api/analyze/.

URL = "/api/analyze/"
RESUME_TOO_LONG = "a" * 30_001
JOB_TOO_LONG = "a" * 20_001

@pytest.fixture
def valid_payload():
    return {
        "resume_text": "Junior developer. Helped with testing. Worked on APIs.",  # contains the fake's original
        "job_description": "The job requirements"
    }


def test_valid_request(api_client, valid_payload):
    response = api_client.post(URL, valid_payload, format="json")
    assert response.status_code == 200
    assert "suggestions" in response.data
    for s in response.data["suggestions"]:
        assert set(s) == {"original", "replacement", "reason"}

def test_missing_resume_text(api_client, valid_payload):
    payload = dict(valid_payload)
    payload.pop("resume_text")
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "resume_text" in response.data

def test_missing_job_description(api_client, valid_payload):
    payload = dict(valid_payload)
    payload.pop("job_description")
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "job_description" in response.data

def test_blank_resume_text(api_client, valid_payload):
    payload = {**valid_payload, "resume_text": " "}
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "resume_text" in response.data

def test_blank_job_description(api_client, valid_payload):
    payload = {**valid_payload, "job_description": " "}
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "job_description" in response.data

def test_resume_text_over_length(api_client, valid_payload):
    payload = {**valid_payload, "resume_text": RESUME_TOO_LONG}
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "resume_text" in response.data

def test_job_description_over_length(api_client, valid_payload):
    payload = {**valid_payload, "job_description": JOB_TOO_LONG}
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 400
    assert "job_description" in response.data

def test_get_is_not_allowed(api_client):
    response = api_client.get(URL)
    assert response.status_code == 405

def test_schema_lists_the_endpoint(api_client):
    response = api_client.get("/api/schema/")
    assert response.status_code == 200
    assert URL in response.data["paths"]


# ---- Milestone 3: AI failures -------------------------------------------------
# Each test replaces the autouse fake for this test only, by patching the same name.
FAKE_PATH = "analysis.services.get_suggestions"


def test_ai_bad_output_returns_502(api_client, valid_payload, monkeypatch):
    def fake(resume_text, job_description):
        raise AIBadOutput()

    monkeypatch.setattr(FAKE_PATH, fake)
    response = api_client.post(URL, valid_payload, format="json")
    assert response.status_code == 502
    assert "detail" in response.data


def test_ai_unavailable_returns_503(api_client, valid_payload, monkeypatch):
    def fake(resume_text, job_description):
        raise AIUnavailable()

    monkeypatch.setattr(FAKE_PATH, fake)
    response = api_client.post(URL, valid_payload, format="json")
    assert response.status_code == 503
    assert "detail" in response.data


def test_original_not_in_resume_returns_502(api_client, valid_payload, monkeypatch):
    invented = [{"original": "Led a team of 50.", "replacement": "Led a team of 50 engineers.", "reason": "x"}]
    monkeypatch.setattr(FAKE_PATH, lambda resume_text, job_description: invented)
    response = api_client.post(URL, valid_payload, format="json")
    assert response.status_code == 502


def test_original_matches_across_line_breaks(api_client, valid_payload, monkeypatch):
    payload = {**valid_payload, "resume_text": "Junior developer. Helped with\ntesting. Worked on APIs."}
    suggestion = [{"original": "Helped with testing.", "replacement": "Wrote tests.", "reason": "x"}]
    monkeypatch.setattr(FAKE_PATH, lambda resume_text, job_description: suggestion)
    response = api_client.post(URL, payload, format="json")
    assert response.status_code == 200
    assert response.data["suggestions"][0]["original"] == "Helped with testing."

