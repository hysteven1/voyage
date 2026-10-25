import pytest

from app.temporal_config import connection_options


def test_local_temporal_defaults(monkeypatch):
    for key in ('TEMPORAL_API_KEY', 'TEMPORAL_TLS', 'TEMPORAL_NAMESPACE'):
        monkeypatch.delenv(key, raising=False)
    assert connection_options() == {'namespace': 'default', 'tls': False}


def test_managed_temporal_requires_tls(monkeypatch):
    monkeypatch.setenv('TEMPORAL_API_KEY', 'unit-only')
    monkeypatch.setenv('TEMPORAL_NAMESPACE', 'test-namespace')
    monkeypatch.delenv('TEMPORAL_TLS', raising=False)
    assert connection_options() == {'namespace': 'test-namespace', 'tls': True, 'api_key': 'unit-only'}
    monkeypatch.setenv('TEMPORAL_TLS', 'false')
    with pytest.raises(ValueError, match='TLS'):
        connection_options()
