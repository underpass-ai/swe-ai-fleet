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
    from core.agents_and_tools.adapters.model_loaders import OllamaModel

    def _assert_req(req: Any) -> None:
        # Request has attributes: full_url or selector
        url = getattr(req, "full_url", getattr(req, "selector", ""))
        assert url.endswith("/api/generate")

    fake = _fake_urlopen_factory(_assert_req, payload={"response": "hello"})
    import core.agents_and_tools.adapters.model_loaders as loaders

    monkeypatch.setattr(loaders, "urlopen", fake)
    # Use test endpoint (from config in real usage)
    m = OllamaModel(model="llama3", endpoint="http://test-ollama:11434")
    out = m.infer("Hi")
    assert out == "hello"


def test_ollama_infer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.error import URLError

    import core.agents_and_tools.adapters.model_loaders as loaders

    def _boom(*_a: Any, **_k: Any):  # noqa: ANN401
        raise URLError("down")

    monkeypatch.setattr(loaders, "urlopen", _boom)
    # Use test endpoint (from config in real usage)
    m = loaders.OllamaModel(model="llama3", endpoint="http://test-ollama:11434")
    with pytest.raises(RuntimeError):
        m.infer("x")


def test_vllm_infer_success_v1_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.agents_and_tools.adapters.model_loaders as loaders

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
    # Use test endpoint (from config in real usage)
    m = loaders.VLLMModel(model="foo", endpoint="http://test-vllm:8000/v1")
    out = m.infer("prompt")
    assert out == "ok"


def test_vllm_infer_success_root_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.agents_and_tools.adapters.model_loaders as loaders

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
    # Use test endpoint (from config in real usage)
    m = loaders.VLLMModel(model="foo", endpoint="http://test-vllm:8000")
    out = m.infer("prompt")
    assert out == "ok2"


def test_vllm_infer_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from urllib.error import HTTPError

    import core.agents_and_tools.adapters.model_loaders as loaders

    def _boom(*_a: Any, **_k: Any):  # noqa: ANN401
        raise HTTPError(url="http://x", code=500, msg="boom", hdrs=None, fp=None)

    monkeypatch.setattr(loaders, "urlopen", _boom)
    # Use test endpoint (from config in real usage)
    m = loaders.VLLMModel(model="m", endpoint="http://test-vllm:8000/v1")
    with pytest.raises(RuntimeError):
        m.infer("x")


def test_get_model_from_env_selects(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.agents_and_tools.adapters.model_loaders as loaders

    # Test vLLM backend
    monkeypatch.setenv("LLM_BACKEND", "vllm")
    monkeypatch.setenv("VLLM_ENDPOINT", "http://vllm:8000/v1")
    monkeypatch.setenv("VLLM_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
    mv = loaders.get_model_from_env()
    assert mv.__class__.__name__ == "VLLMModel"
    
    # Test Ollama backend
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1")
    mo = loaders.get_model_from_env()
    assert mo.__class__.__name__ == "OllamaModel"
    
    # Test missing LLM_BACKEND fails fast
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    with pytest.raises(ValueError, match="LLM_BACKEND environment variable must be set"):
        loaders.get_model_from_env()
    
    # Test missing VLLM_ENDPOINT fails fast
    monkeypatch.setenv("LLM_BACKEND", "vllm")
    monkeypatch.delenv("VLLM_ENDPOINT", raising=False)
    with pytest.raises(ValueError, match="VLLM_ENDPOINT environment variable must be set"):
        loaders.get_model_from_env()


