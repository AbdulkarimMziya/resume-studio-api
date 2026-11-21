import pytest



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
        "resume_text": "Your resume text",
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
