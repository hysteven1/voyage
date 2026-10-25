import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.health import status


@pytest.mark.parametrize('running,shutdown,healthy,expected', [
    (True, False, True, 200), (False, False, True, 503),
    (True, True, True, 503), (True, False, False, 503),
])
def test_readiness_reflects_worker_and_temporal(running, shutdown, healthy, expected):
    worker = SimpleNamespace(is_running=running, is_shutdown=shutdown)
    client = SimpleNamespace(service_client=SimpleNamespace(check_health=AsyncMock(return_value=healthy)))
    assert asyncio.run(status('/health/ready', worker, client)) == expected
    assert asyncio.run(status('/health/live', worker, client)) == 200


def test_readiness_survives_temporal_failure():
    worker = SimpleNamespace(is_running=True, is_shutdown=False)
    client = SimpleNamespace(service_client=SimpleNamespace(check_health=AsyncMock(side_effect=RuntimeError())))
    assert asyncio.run(status('/health/ready', worker, client)) == 503
    assert asyncio.run(status('/missing', worker, client)) == 404
