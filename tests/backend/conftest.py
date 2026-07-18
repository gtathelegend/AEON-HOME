"""conftest.py — pytest configuration for ÆON backend tests."""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark a test as async"
    )
