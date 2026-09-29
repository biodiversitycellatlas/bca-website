import pytest
import os


@pytest.fixture()
def browser_context_args(browser_context_args):
    base_url = os.getenv("PYTEST_BASE_URL", "http://web:8000")
    return {**browser_context_args, "base_url": base_url}
