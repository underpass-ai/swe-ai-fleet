"""Tests for model_loaders module."""

import json
from unittest.mock import Mock, patch
from urllib.error import URLError

import pytest
from core.agents_and_tools.adapters.model_loaders import (
    LlamaCppModel,
    OllamaModel,
    VLLMModel,
    get_model_from_env,
)


class TestLlamaCppModel:
    """Test suite for LlamaCppModel."""

    def test_init_with_defaults(self):
        """Test initialization with default n_ctx."""
        model = LlamaCppModel(gguf_path="/path/to/model.gguf")

        assert model._gguf_path == "/path/to/model.gguf"
        assert model._n_ctx == 8192

    def test_init_with_custom_n_ctx(self):
        """Test initialization with custom n_ctx."""
        model = LlamaCppModel(gguf_path="/path/to/model.gguf", n_ctx=4096)

        assert model._gguf_path == "/path/to/model.gguf"
        assert model._n_ctx == 4096

    def test_infer_raises_not_implemented_error(self):
        """Test that infer raises NotImplementedError."""
        model = LlamaCppModel(gguf_path="/path/to/model.gguf")

        with pytest.raises(NotImplementedError) as exc_info:
            model.infer("test prompt")

        assert "llama.cpp bindings are not yet integrated" in str(exc_info.value)
        assert "Use 'vllm' or 'ollama' backend instead" in str(exc_info.value)

    def test_infer_with_kwargs_raises_not_implemented_error(self):
        """Test that infer raises NotImplementedError even with kwargs."""
        model = LlamaCppModel(gguf_path="/path/to/model.gguf")

        with pytest.raises(NotImplementedError):
            model.infer("test prompt", temperature=0.7, max_tokens=100)


class TestOllamaModel:
    """Test suite for OllamaModel."""

    def test_init_raises_error_on_empty_endpoint(self):
        """Test that initialization raises ValueError for empty endpoint."""
        with pytest.raises(ValueError, match="endpoint cannot be empty"):
            OllamaModel(model="test-model", endpoint="")

    def test_init_strips_trailing_slash(self):
        """Test that endpoint trailing slashes are stripped."""
        model = OllamaModel(model="test-model", endpoint="http://localhost:11434/")

        assert model._model == "test-model"
        assert model._endpoint == "http://localhost:11434"

    def test_init_with_valid_params(self):
        """Test initialization with valid parameters."""
        model = OllamaModel(model="test-model", endpoint="http://localhost:11434")

        assert model._model == "test-model"
        assert model._endpoint == "http://localhost:11434"

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    @patch("core.agents_and_tools.adapters.model_loaders.time.time")
    def test_infer_success(self, mock_time, mock_urlopen):
        """Test successful inference."""
        mock_time.side_effect = [0.0, 0.5]  # start, end times
        mock_response = Mock()
        mock_response.read.return_value = b'{"response": "Hello, world!"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        model = OllamaModel(model="test-model", endpoint="http://localhost:11434")
        result = model.infer("test prompt")

        assert result == "Hello, world!"
        mock_urlopen.assert_called_once()
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_method() == "POST"
        assert call_args.get_full_url() == "http://localhost:11434/api/generate"

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    @patch("core.agents_and_tools.adapters.model_loaders.time.time")
    def test_infer_with_custom_params(self, mock_time, mock_urlopen):
        """Test inference with custom parameters."""
        mock_time.side_effect = [0.0, 0.5]
        mock_response = Mock()
        mock_response.read.return_value = b'{"response": "Custom response"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        model = OllamaModel(model="test-model", endpoint="http://localhost:11434")
        kwargs = {"model": "custom-model", "options": {"temperature": 0.7}, "timeout_sec": 120}
        result = model.infer("test prompt", **kwargs)

        assert result == "Custom response"
        call_args = mock_urlopen.call_args[0][0]
        payload = json.loads(call_args.data.decode("utf-8"))
        assert payload["model"] == "custom-model"
        assert payload["options"] == {"temperature": 0.7}

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    def test_infer_raises_runtime_error_on_urlerror(self, mock_urlopen):
        """Test that URLError is converted to RuntimeError."""
        mock_urlopen.side_effect = URLError("Connection failed")

        model = OllamaModel(model="test-model", endpoint="http://localhost:11434")

        with pytest.raises(RuntimeError, match="Ollama request failed"):
            model.infer("test prompt")


class TestVLLMModel:
    """Test suite for VLLMModel."""

    def test_init_raises_error_on_empty_endpoint(self):
        """Test that initialization raises ValueError for empty endpoint."""
        with pytest.raises(ValueError, match="endpoint cannot be empty"):
            VLLMModel(model="test-model", endpoint="")

    def test_init_strips_trailing_slash(self):
        """Test that endpoint trailing slashes are stripped."""
        model = VLLMModel(model="test-model", endpoint="http://localhost:8000/v1/")

        assert model._model == "test-model"
        assert model._endpoint == "http://localhost:8000/v1"

    def test_init_with_valid_params(self):
        """Test initialization with valid parameters."""
        model = VLLMModel(model="test-model", endpoint="http://localhost:8000/v1")

        assert model._model == "test-model"
        assert model._endpoint == "http://localhost:8000/v1"

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    @patch("core.agents_and_tools.adapters.model_loaders.time.time")
    def test_infer_success_with_v1_endpoint(self, mock_time, mock_urlopen):
        """Test successful inference with /v1 endpoint."""
        mock_time.side_effect = [0.0, 0.5]
        mock_response = Mock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "Hello!"}}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        model = VLLMModel(model="test-model", endpoint="http://localhost:8000/v1")
        result = model.infer("test prompt")

        assert result == "Hello!"
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_full_url() == "http://localhost:8000/v1/chat/completions"

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    @patch("core.agents_and_tools.adapters.model_loaders.time.time")
    def test_infer_success_without_v1_endpoint(self, mock_time, mock_urlopen):
        """Test successful inference without /v1 in endpoint."""
        mock_time.side_effect = [0.0, 0.5]
        mock_response = Mock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "World!"}}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        model = VLLMModel(model="test-model", endpoint="http://localhost:8000")
        result = model.infer("test prompt")

        assert result == "World!"
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.get_full_url() == "http://localhost:8000/v1/chat/completions"

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    @patch("core.agents_and_tools.adapters.model_loaders.time.time")
    def test_infer_with_custom_messages(self, mock_time, mock_urlopen):
        """Test inference with custom messages."""
        mock_time.side_effect = [0.0, 0.5]
        mock_response = Mock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "Custom"}}]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        model = VLLMModel(model="test-model", endpoint="http://localhost:8000/v1")
        messages = [{"role": "system", "content": "You are helpful"}]
        result = model.infer("test prompt", messages=messages)

        assert result == "Custom"
        call_args = mock_urlopen.call_args[0][0]
        payload = json.loads(call_args.data.decode("utf-8"))
        assert payload["messages"] == messages

    @patch("core.agents_and_tools.adapters.model_loaders.urlopen")
    def test_infer_raises_runtime_error_on_urlerror(self, mock_urlopen):
        """Test that URLError is converted to RuntimeError."""
        mock_urlopen.side_effect = URLError("Connection failed")

        model = VLLMModel(model="test-model", endpoint="http://localhost:8000/v1")

        with pytest.raises(RuntimeError, match="vLLM request failed"):
            model.infer("test prompt")


class TestGetModelFromEnv:
    """Test suite for get_model_from_env function."""

    def test_raises_error_when_llm_backend_not_set(self, monkeypatch):
        """Test that ValueError is raised when LLM_BACKEND is not set."""
        monkeypatch.delenv("LLM_BACKEND", raising=False)

        with pytest.raises(ValueError, match="LLM_BACKEND environment variable must be set"):
            get_model_from_env()

    def test_raises_error_for_unknown_backend(self, monkeypatch):
        """Test that ValueError is raised for unknown backend."""
        monkeypatch.setenv("LLM_BACKEND", "unknown")

        with pytest.raises(ValueError, match="Unknown LLM_BACKEND: unknown"):
            get_model_from_env()

    def test_returns_vllm_model_when_configured(self, monkeypatch):
        """Test that VLLMModel is returned when vllm backend is configured."""
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        monkeypatch.setenv("VLLM_ENDPOINT", "http://localhost:8000/v1")
        monkeypatch.setenv("VLLM_MODEL", "test-model")

        model = get_model_from_env()

        assert isinstance(model, VLLMModel)
        assert model._model == "test-model"
        assert model._endpoint == "http://localhost:8000/v1"

    def test_raises_error_when_vllm_endpoint_missing(self, monkeypatch):
        """Test that ValueError is raised when VLLM_ENDPOINT is missing."""
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        monkeypatch.delenv("VLLM_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="VLLM_ENDPOINT environment variable must be set"):
            get_model_from_env()

    def test_raises_error_when_vllm_model_missing(self, monkeypatch):
        """Test that ValueError is raised when VLLM_MODEL is missing."""
        monkeypatch.setenv("LLM_BACKEND", "vllm")
        monkeypatch.setenv("VLLM_ENDPOINT", "http://localhost:8000/v1")
        monkeypatch.delenv("VLLM_MODEL", raising=False)

        with pytest.raises(ValueError, match="VLLM_MODEL environment variable must be set"):
            get_model_from_env()

    def test_returns_ollama_model_when_configured(self, monkeypatch):
        """Test that OllamaModel is returned when ollama backend is configured."""
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        monkeypatch.setenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")

        model = get_model_from_env()

        assert isinstance(model, OllamaModel)
        assert model._model == "test-model"
        assert model._endpoint == "http://localhost:11434"

    def test_raises_error_when_ollama_endpoint_missing(self, monkeypatch):
        """Test that ValueError is raised when OLLAMA_ENDPOINT is missing."""
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        monkeypatch.delenv("OLLAMA_ENDPOINT", raising=False)

        with pytest.raises(ValueError, match="OLLAMA_ENDPOINT environment variable must be set"):
            get_model_from_env()

    def test_raises_error_when_ollama_model_missing(self, monkeypatch):
        """Test that ValueError is raised when OLLAMA_MODEL is missing."""
        monkeypatch.setenv("LLM_BACKEND", "ollama")
        monkeypatch.setenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        with pytest.raises(ValueError, match="OLLAMA_MODEL environment variable must be set"):
            get_model_from_env()

    def test_returns_llamacpp_model_when_configured(self, monkeypatch):
        """Test that LlamaCppModel is returned when llamacpp backend is configured."""
        monkeypatch.setenv("LLM_BACKEND", "llamacpp")
        monkeypatch.setenv("GGUF_PATH", "/path/to/model.gguf")

        model = get_model_from_env()

        assert isinstance(model, LlamaCppModel)
        assert model._gguf_path == "/path/to/model.gguf"
        assert model._n_ctx == 8192

    def test_returns_llamacpp_model_with_custom_n_ctx(self, monkeypatch):
        """Test that LlamaCppModel uses custom N_CTX when set."""
        monkeypatch.setenv("LLM_BACKEND", "llamacpp")
        monkeypatch.setenv("GGUF_PATH", "/path/to/model.gguf")
        monkeypatch.setenv("N_CTX", "4096")

        model = get_model_from_env()

        assert isinstance(model, LlamaCppModel)
        assert model._gguf_path == "/path/to/model.gguf"
        assert model._n_ctx == 4096

    def test_raises_error_when_gguf_path_missing(self, monkeypatch):
        """Test that ValueError is raised when GGUF_PATH is missing."""
        monkeypatch.setenv("LLM_BACKEND", "llamacpp")
        monkeypatch.delenv("GGUF_PATH", raising=False)

        with pytest.raises(ValueError, match="GGUF_PATH environment variable must be set"):
            get_model_from_env()

    def test_backend_case_insensitive(self, monkeypatch):
        """Test that backend is case-insensitive."""
        monkeypatch.setenv("LLM_BACKEND", "VLLM")
        monkeypatch.setenv("VLLM_ENDPOINT", "http://localhost:8000/v1")
        monkeypatch.setenv("VLLM_MODEL", "test-model")

        model = get_model_from_env()

        assert isinstance(model, VLLMModel)

