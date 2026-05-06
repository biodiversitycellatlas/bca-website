import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="class")
def live_server_url(request):
    """Provide live server URL to test class."""
    server = StaticLiveServerTestCase
    server.setUpClass()
    request.addfinalizer(server.tearDownClass)
    return server.live_server_url


@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture(scope="session")
def browser():
    """Create browser instance for test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()
