import asyncio
import logging
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import Request, Response

from app import main
from app.logging_config import JsonFormatter


def test_json_formatter(monkeypatch):
    import json

    monkeypatch.setenv("SERVICE_NAME", "trip-service")
    record = logging.LogRecord("voyage.api", logging.INFO, "", 0, "Hello %s", ("world",), None)
    record.request_id = "request-id"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "Hello world"
    assert payload["service"] == "trip-service"
    assert payload["request_id"] == "request-id"
    assert payload["timestamp"].endswith("+00:00")


def test_request_logging_and_unique_ids(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(main, "logger", logger)
    ids = []

    async def respond(request):
        return Response(status_code=201)

    for _ in range(2):
        request = Request({"type": "http", "method": "POST", "path": "/api/v1/trips", "headers": []})
        response = asyncio.run(main.request_logging_middleware(request, respond))
        request_id = response.headers["X-Request-ID"]
        UUID(request_id)
        assert request.state.request_id == request_id
        fields = logger.info.call_args.kwargs["extra"]
        assert fields["status_code"] == 201
        assert fields["method"] == "POST"
        assert fields["path"] == "/api/v1/trips"
        assert fields["duration_ms"] >= 0
        ids.append(request_id)
    assert ids[0] != ids[1]


def test_request_failure_is_logged_and_reraised(monkeypatch):
    logger = Mock()
    monkeypatch.setattr(main, "logger", logger)
    failure = RuntimeError("Request failed")

    async def fail(request):
        raise failure

    request = Request({"type": "http", "method": "GET", "path": "/failure", "headers": []})
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(main.request_logging_middleware(request, fail))
    assert caught.value is failure
    assert logger.exception.call_args.kwargs["extra"]["request_id"] == request.state.request_id
