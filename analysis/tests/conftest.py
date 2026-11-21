import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    # Named api_client (not client) so it doesn't hide pytest-django's built-in `client` fixture.
    return APIClient()
