"""Unit tests never consume configured provider credentials or paid searches."""

import pytest


@pytest.fixture(autouse=True)
def no_live_credentials(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
