from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest


def _fake_urlopen_factory(assert_fn: Callable[[Any], None], payload: dict[str, Any]):
    class _Resp:
        def __init__(self, body: str) -> None:
            self._body = body.encode("utf-8")

        def read(self) -> bytes:  # noqa: D401
            return self._body

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_: Any) -> None:  # noqa: ANN401
            return None

    def _fake_urlopen(request: Any, timeout: float | int | None = None):  # noqa: ANN401
        assert_fn(request)
        _ = timeout
        return _Resp(json.dumps(payload))

    return _fake_urlopen


def test_ollama_infer_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from swe_ai_fleet.models.loaders import OllamaModel

    def _assert_req(req: Any) -> None:
        # Request has attributes: full_url or selector
        url = getattr(req, "full_url", getattr(req, "selector", ""))
        assert url.endswith("/api/generate")

    fake = _fake_urlopen_factory(_assert_req, payload={"response": "hello"})
    import swe_ai_fleet.models.loaders as loaders

    monkeypatch.setattr(loaders, "urlopen", fake)
    m = OllamaModel(model="llama3", endpoint="http://host:11434")
    out = m.infer("Hi")
    assert out == "hello"


def test_ollama_infer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.error import URLError

    import swe_ai_fleet.models.loaders as loaders

    def _boom(*_a: Any, **_k: Any):  # noqa: ANN401
        raise URLError("down")

    monkeypatch.setattr(loaders, "urlopen", _boom)
    m = loaders.OllamaModel()
    with pytest.raises(RuntimeError):
        m.infer("x")


def test_vllm_infer_success_v1_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    import swe_ai_fleet.models.loaders as loaders

    def _assert_req(req: Any) -> None:
        url = getattr(req, "full_url", getattr(req, "selector", ""))
        # When endpoint ends with /v1, path should be /chat/completions
        assert url.endswith("/chat/completions")

    fake = _fake_urlopen_factory(
        _assert_req,
        payload={
            "choices": [
                {"message": {"content": "ok"}},
            ]
        },
    )
    monkeypatch.setattr(loaders, "urlopen", fake)
    m = loaders.VLLMModel(model="foo", endpoint="http://localhost:8000/v1")
    out = m.infer("prompt")
    assert out == "ok"


def test_vllm_infer_success_root_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    import swe_ai_fleet.models.loaders as loaders

    def _assert_req(req: Any) -> None:
        url = getattr(req, "full_url", getattr(req, "selector", ""))
        # When endpoint is root, path should be /v1/chat/completions
        assert url.endswith("/v1/chat/completions")

    fake = _fake_urlopen_factory(
        _assert_req,
        payload={
            "choices": [
                {"message": {"content": "ok2"}},
            ]
        },
    )
    monkeypatch.setattr(loaders, "urlopen", fake)
    m = loaders.VLLMModel(model="foo", endpoint="http://localhost:8000")
    out = m.infer("prompt")
    assert out == "ok2"


def test_vllm_infer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.error import HTTPError

    import swe_ai_fleet.models.loaders as loaders

    def _boom(*_a: Any, **_k: Any):  # noqa: ANN401
        raise HTTPError(url="http://x", code=500, msg="boom", hdrs=None, fp=None)

    monkeypatch.setattr(loaders, "urlopen", _boom)
    m = loaders.VLLMModel(model="m")
    with pytest.raises(RuntimeError):
        m.infer("x")


def test_get_model_from_env_selects(monkeypatch: pytest.MonkeyPatch) -> None:
    import swe_ai_fleet.models.loaders as loaders

    # Default: ollama
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    m = loaders.get_model_from_env()
    assert m.__class__.__name__ == "OllamaModel"

    # vLLM explicit
    monkeypatch.setenv("LLM_BACKEND", "vllm")
    monkeypatch.setenv("VLLM_MODEL", "bar")
    mv = loaders.get_model_from_env()
    assert mv.__class__.__name__ == "VLLMModel"


