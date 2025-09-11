from __future__ import annotations

import json
import os
import time
from typing import Protocol
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class Model(Protocol):
    def infer(self, prompt: str, **kwargs) -> str: ...


class LlamaCppModel:
    def __init__(self, gguf_path: str, n_ctx: int = 8192) -> None:
        self._gguf_path = gguf_path
        self._n_ctx = n_ctx

    def infer(self, prompt: str, **kwargs) -> str:
        # TODO: integrate llama.cpp bindings
        return "TODO: inference result"


class OllamaModel:
    def __init__(self, model: str = "llama3.1", endpoint: str = "http://localhost:11434") -> None:
        self._model = model
        self._endpoint = endpoint.rstrip("/")

    def infer(self, prompt: str, **kwargs) -> str:
        """Call Ollama generate endpoint (non-stream) and return the response text.

        Args:
            prompt: Prompt text
            model: Optional override of model name
            options: Dict of generation options (temperature, top_p, etc.)
            timeout_sec: Request timeout in seconds (default 60)
        """
        model = kwargs.get("model", self._model)
        options = kwargs.get("options", {})
        timeout_sec = float(kwargs.get("timeout_sec", 60))
        payload = {
            "model": model,
            "prompt": prompt,
            "options": options,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            url=f"{self._endpoint}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            start = time.time()
            with urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode("utf-8")
            dur = (time.time() - start) * 1000.0  # ms
            obj = json.loads(body)
            text = obj.get("response") or obj.get("data") or ""
            # Attach simple usage metrics in kwargs (side-channel)
            kwargs["_usage_ms"] = int(dur)
            return text
        except (HTTPError, URLError) as e:
            raise RuntimeError(f"Ollama request failed: {e}")


class VLLMModel:
    """OpenAI-compatible client for vLLM server (chat completions).

    Default endpoint: http://localhost:8000/v1
    """

    def __init__(self, model: str, endpoint: str = "http://localhost:8000/v1") -> None:
        self._model = model
        self._endpoint = endpoint.rstrip("/")

    def infer(self, prompt: str, **kwargs) -> str:
        messages = kwargs.get("messages") or [{"role": "user", "content": prompt}]
        temperature = kwargs.get("temperature", 0.2)
        timeout_sec = float(kwargs.get("timeout_sec", 60))
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            url=f"{self._endpoint}/chat/completions" if self._endpoint.endswith("/v1") else f"{self._endpoint}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            start = time.time()
            with urlopen(req, timeout=timeout_sec) as resp:
                body = resp.read().decode("utf-8")
            dur = (time.time() - start) * 1000.0
            obj = json.loads(body)
            text = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
            kwargs["_usage_ms"] = int(dur)
            return text
        except (HTTPError, URLError) as e:
            raise RuntimeError(f"vLLM request failed: {e}")


def get_model_from_env() -> Model:
    """Return a Model based on env configuration.

    LLM_BACKEND: 'vllm' | 'ollama' (default: 'ollama')
    For vLLM: VLLM_ENDPOINT (default http://localhost:8000/v1), VLLM_MODEL (required)
    For Ollama: OLLAMA_ENDPOINT (default http://localhost:11434), OLLAMA_MODEL (default llama3.1)
    """
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    if backend == "vllm":
        endpoint = os.getenv("VLLM_ENDPOINT", "http://localhost:8000/v1")
        model = os.getenv("VLLM_MODEL") or "llama3.1"  # set a reasonable default if not provided
        return VLLMModel(model=model, endpoint=endpoint)
    else:
        endpoint = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.1")
        return OllamaModel(model=model, endpoint=endpoint)
