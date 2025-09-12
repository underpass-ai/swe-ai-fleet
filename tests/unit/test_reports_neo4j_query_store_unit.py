from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch


def _fake_driver_with_results(rows: list[dict[str, Any]]):
    class _FakeSession:
        def __init__(self, rows: list[dict[str, Any]]):
            self._rows = rows

        def run(self, cypher: str, params: dict[str, Any] | None = None):  # noqa: ARG001
            return self._rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401, ANN001, ANN201
            return False

    class _FakeDriver:
        def __init__(self, rows: list[dict[str, Any]]):
            self._rows = rows

        def session(self, database=None):  # noqa: ANN001, D401
            return _FakeSession(self._rows)

        def close(self):  # noqa: D401, ANN201
            return None

    return _FakeDriver(rows)


def test_query_success():
    # Patch GraphDatabase in the module under test
    from swe_ai_fleet.reports.adapters import neo4j_query_store as nq

    fake_driver = _fake_driver_with_results([{"ok": 1}])
    with patch.object(nq, "GraphDatabase", SimpleNamespace(driver=MagicMock(return_value=fake_driver))):
        store = nq.Neo4jQueryStore()
        out = store.query("RETURN 1")
        assert out == [{"ok": 1}]
        store.close()


def test_query_retry_then_success():
    from swe_ai_fleet.reports.adapters import neo4j_query_store as nq

    class RetryErr(Exception):
        pass

    # Override exception classes used in except tuple
    nq.ServiceUnavailable = RetryErr  # type: ignore
    nq.TransientError = RetryErr  # type: ignore

    class _RetrySession:
        def __init__(self):
            self.calls = 0

        def run(self, cypher: str, params: dict[str, Any] | None = None):  # noqa: ARG001
            return [{"v": 42}]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: D401, ANN001, ANN201
            return False

    sess = _RetrySession()

    def _session_side_effect():
        if sess.calls == 0:
            sess.calls += 1
            raise RetryErr("transient")
        return sess

    # Patch GraphDatabase to avoid ImportError and patch _session to raise then succeed
    with patch.object(
        nq,
        "GraphDatabase",
        SimpleNamespace(driver=MagicMock(return_value=SimpleNamespace(close=lambda: None))),
    ):
        store = nq.Neo4jQueryStore()
        # Monkeypatch the instance _session
        store._session = _session_side_effect  # type: ignore[assignment]
        out = store.query("RETURN 1")
        assert out == [{"v": 42}]
        store.close()


