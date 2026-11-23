import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle

ANALYZE_URL = "/api/analyze/"
EXTRACT_URL = "/api/extract-text/"
PAYLOAD = {
    "resume_text": "Junior developer. Helped with testing. Worked on APIs.",  # contains the fake's original
    "job_description": "The job requirements",
}

# Generous defaults so only the throttle a test is about can trigger
RATES = {
    "analyze_burst": "100/min",
    "analyze_daily": "100/day",
    "analyze_global": "100/day",
    "extract": "100/min",
}


@pytest.fixture
def set_rates(monkeypatch):
    """DRF copies the rates onto the throttle classes when it's imported, so changing settings
    in a test does nothing. Patch the copy instead."""
    def _set(**overrides):
        monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {**RATES, **overrides})
    _set()
    return _set


@pytest.fixture
def gemini_calls(monkeypatch, fake_gemini):
    """Count how many requests actually reached the (fake) Gemini call."""
    calls = []

    def fake(resume_text, job_description):
        calls.append(1)
        return fake_gemini

    monkeypatch.setattr("analysis.services.get_suggestions", fake)
    return calls


def analyze(api_client, ip="1.1.1.1", **extra):
    return api_client.post(ANALYZE_URL, PAYLOAD, format="json", REMOTE_ADDR=ip, **extra)


def extract(api_client, ip="1.1.1.1"):
    file = SimpleUploadedFile("cv.txt", b"Junior developer.", content_type="text/plain")
    return api_client.post(EXTRACT_URL, {"file": file}, format="multipart", REMOTE_ADDR=ip)


def test_burst_limit_returns_429_and_skips_gemini(api_client, set_rates, gemini_calls):
    set_rates(analyze_burst="5/min")
    for _ in range(5):
        assert analyze(api_client).status_code == 200

    response = analyze(api_client)

    assert response.status_code == 429
    assert "detail" in response.data
    assert int(response["Retry-After"]) > 0
    assert len(gemini_calls) == 5            # the throttled request never reached Gemini


def test_daily_limit(api_client, set_rates):
    set_rates(analyze_daily="3/day")
    for _ in range(3):
        assert analyze(api_client).status_code == 200
    assert analyze(api_client).status_code == 429


def test_limits_are_per_ip(api_client, set_rates):
    set_rates(analyze_burst="2/min")
    analyze(api_client, ip="1.1.1.1")
    analyze(api_client, ip="1.1.1.1")
    assert analyze(api_client, ip="1.1.1.1").status_code == 429
    assert analyze(api_client, ip="2.2.2.2").status_code == 200     # someone else isn't affected


def test_global_cap_is_shared_by_everyone(api_client, set_rates):
    set_rates(analyze_global="2/day")
    assert analyze(api_client, ip="1.1.1.1").status_code == 200
    assert analyze(api_client, ip="2.2.2.2").status_code == 200
    assert analyze(api_client, ip="3.3.3.3").status_code == 429     # a new IP doesn't get around it


def test_extract_has_its_own_limit(api_client, set_rates):
    set_rates(extract="2/min", analyze_burst="1/min")
    assert analyze(api_client).status_code == 200
    assert analyze(api_client).status_code == 429                   # analyze is used up...
    assert extract(api_client).status_code == 200                   # ...extract still works
    assert extract(api_client).status_code == 200
    assert extract(api_client).status_code == 429


def test_behind_one_proxy_the_client_cant_fake_its_ip(api_client, set_rates, monkeypatch):
    # On Render (NUM_PROXIES=1) the real IP is the LAST X-Forwarded-For entry, added by Render.
    # A client can put anything in front of it, and that must not give it a fresh limit.
    api_settings.NUM_PROXIES                                        # load the setting before patching
    monkeypatch.setattr(api_settings, "NUM_PROXIES", 1)
    set_rates(analyze_burst="2/min")

    def via_proxy(fake_ip):
        return analyze(api_client, ip="10.0.0.1", HTTP_X_FORWARDED_FOR=f"{fake_ip}, 203.0.113.7")

    assert via_proxy("9.9.9.1").status_code == 200
    assert via_proxy("9.9.9.2").status_code == 200
    assert via_proxy("9.9.9.3").status_code == 429


@override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
def test_frontend_can_read_retry_after(api_client, set_rates):
    set_rates(analyze_burst="1/min")
    analyze(api_client, HTTP_ORIGIN="http://localhost:5173")
    response = analyze(api_client, HTTP_ORIGIN="http://localhost:5173")

    assert response.status_code == 429
    assert response["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Retry-After" in response["Access-Control-Expose-Headers"]
