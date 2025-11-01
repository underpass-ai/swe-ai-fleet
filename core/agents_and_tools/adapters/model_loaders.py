from __future__ import annotations

import json
import os
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class Model(Protocol):
    def infer(self, prompt: str, **kwargs) -> str: ...


class LlamaCppModel:
    def __init__(self, gguf_path: str, n_ctx: int = 8192) -> None:
        self._gguf_path = gguf_path
        self._n_ctx = n_ctx

    def infer(self, _prompt: str, **kwargs) -> str:
        """Inference method (placeholder for llama.cpp integration).
        
        Args:
            _prompt: Input prompt (unused, TODO: integrate llama.cpp)
            **kwargs: Additional inference parameters
        """
        # TODO: integrate llama.cpp bindings
        return "TODO: inference result"


class OllamaModel:
    """Ollama model client.
    
    Endpoint should be configured via environment variable OLLAMA_ENDPOINT.
    """
    
    def __init__(self, model: str, endpoint: str) -> None:
        """Initialize Ollama model client.
        
        Args:
            model: Model name
            endpoint: Full endpoint URL (from environment variable, e.g., OLLAMA_ENDPOINT)
        
        Raises:
            ValueError: If endpoint is empty
        """
        if not endpoint:
            raise ValueError("endpoint cannot be empty - must be provided via OLLAMA_ENDPOINT env var")
        
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
            raise RuntimeError(f"Ollama request failed: {e}") from e


class VLLMModel:
    """OpenAI-compatible client for vLLM server (chat completions).

    Endpoint should be configured via environment variable VLLM_ENDPOINT.
    No default protocol to avoid hardcoding HTTP/HTTPS.
    """

    def __init__(self, model: str, endpoint: str) -> None:
        """Initialize vLLM model client.
        
        Args:
            model: Model name
            endpoint: Full endpoint URL (from environment variable, e.g., VLLM_ENDPOINT)
        
        Raises:
            ValueError: If endpoint is empty
        """
        if not endpoint:
            raise ValueError("endpoint cannot be empty - must be provided via VLLM_ENDPOINT env var")
        
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
        url = (
            f"{self._endpoint}/chat/completions"
            if self._endpoint.endswith("/v1")
            else f"{self._endpoint}/v1/chat/completions"
        )
        req = Request(
            url=url,
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
            raise RuntimeError(f"vLLM request failed: {e}") from e


def get_model_from_env() -> Model:
    """Return a Model based on env configuration.

    Required environment variables:
    - LLM_BACKEND: 'vllm' | 'ollama' | 'llamacpp' (required, no default)
    
    For vLLM backend:
    - VLLM_ENDPOINT: Full URL (required, e.g., 'http://vllm-service:8000/v1' from K8s ConfigMap)
    - VLLM_MODEL: Model name (required)
    
    For Ollama backend:
    - OLLAMA_ENDPOINT: Full URL (required, e.g., 'http://ollama:11434' from K8s ConfigMap)
    - OLLAMA_MODEL: Model name (required)
    
    For Llama.cpp backend:
    - GGUF_PATH: Path to GGUF model file (required)
    - N_CTX: Context length (optional, default 8192)
    
    Note: Endpoints are configured via Kubernetes ConfigMaps/Secrets.
    HTTP is safe for internal cluster communication (not exposed externally).
    
    Raises:
        ValueError: If required environment variables are missing
    """
    backend = os.getenv("LLM_BACKEND")
    if not backend:
        raise ValueError("LLM_BACKEND environment variable must be set (vllm|ollama|llamacpp)")
    
    backend = backend.lower()
    
    if backend == "vllm":
        endpoint = os.getenv("VLLM_ENDPOINT")
        if not endpoint:
            raise ValueError("VLLM_ENDPOINT environment variable must be set")
        
        model = os.getenv("VLLM_MODEL")
        if not model:
            raise ValueError("VLLM_MODEL environment variable must be set")
        
        return VLLMModel(model=model, endpoint=endpoint)
    
    elif backend == "ollama":
        endpoint = os.getenv("OLLAMA_ENDPOINT")
        if not endpoint:
            raise ValueError("OLLAMA_ENDPOINT environment variable must be set")
        
        model = os.getenv("OLLAMA_MODEL")
        if not model:
            raise ValueError("OLLAMA_MODEL environment variable must be set")
        
        return OllamaModel(model=model, endpoint=endpoint)
    
    elif backend == "llamacpp":
        gguf_path = os.getenv("GGUF_PATH")
        if not gguf_path:
            raise ValueError("GGUF_PATH environment variable must be set for llamacpp backend")
        
        n_ctx = int(os.getenv("N_CTX", "8192"))
        return LlamaCppModel(gguf_path=gguf_path, n_ctx=n_ctx)
    
    else:
        raise ValueError(f"Unknown LLM_BACKEND: {backend}. Must be 'vllm', 'ollama', or 'llamacpp'")
