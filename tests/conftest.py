import pytest
from dotenv import load_dotenv

load_dotenv()


def pytest_configure():
    pytest.shared = {}
