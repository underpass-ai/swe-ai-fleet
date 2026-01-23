"""Tests for planning ceremony processor server."""

from unittest.mock import AsyncMock

import pytest

from services.planning_ceremony_processor import server as server_module


@pytest.mark.asyncio
async def test_serve_requires_protobuf_stubs(monkeypatch) -> None:
    monkeypatch.setattr(server_module, "planning_ceremony_pb2_grpc", None)

    with pytest.raises(RuntimeError, match="protobuf stubs not available"):
        await server_module._serve()


def test_main_invokes_asyncio_run(monkeypatch) -> None:
    called = {"value": False}

    def _fake_run(_coro) -> None:
        called["value"] = True

    monkeypatch.setattr(server_module.asyncio, "run", _fake_run)
    monkeypatch.setattr(server_module, "_serve", AsyncMock())

    server_module.main()

    assert called["value"] is True
