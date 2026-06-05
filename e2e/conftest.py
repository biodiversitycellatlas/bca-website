import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


@pytest.fixture(scope="class")
def live_server_url(request):
    """Provide live server URL to test class."""
    server = StaticLiveServerTestCase
    server.setUpClass()
    request.addfinalizer(server.tearDownClass)
    return server.live_server_url
