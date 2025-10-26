"""Tests for VLLMClientAdapter."""

import pytest

from core.agents.infrastructure.adapters.vllm_client_adapter import VLLMClientAdapter


class TestVLLMClientAdapter:
    """Test suite for VLLMClientAdapter."""

    def test_init_with_custom_params(self):
        """Test adapter initialization with custom parameters."""
        adapter = VLLMClientAdapter(
            vllm_url="http://custom-url:9000",
            model="custom-model",
            temperature=0.3,
            max_tokens=4096,
            timeout=120
        )

        assert adapter.vllm_url == "http://custom-url:9000"
        assert adapter.model == "custom-model"
        assert adapter.temperature == 0.3
        assert adapter.max_tokens == 4096
        assert adapter.timeout == 120

    def test_init_strips_trailing_slash(self):
        """Test that vllm_url trailing slashes are stripped."""
        adapter = VLLMClientAdapter(
            vllm_url="http://localhost:8000/",
            model="test-model"
        )

        assert adapter.vllm_url == "http://localhost:8000"

    def test_init_with_defaults(self):
        """Test adapter initialization with default parameters."""
        adapter = VLLMClientAdapter(
            vllm_url="http://localhost:8000"
        )

        assert adapter.vllm_url == "http://localhost:8000"
        assert adapter.model == "Qwen/Qwen3-0.6B"
        assert adapter.temperature == 0.7
        assert adapter.max_tokens == 2048
        assert adapter.timeout == 60

    def test_init_raises_error_if_aiohttp_not_available(self, monkeypatch):
        """Test that ImportError is raised if aiohttp is not available."""
        # Mock aiohttp as unavailable
        monkeypatch.setattr('core.agents.infrastructure.adapters.vllm_client_adapter.aiohttp', None)
        monkeypatch.setattr('core.agents.infrastructure.adapters.vllm_client_adapter.AIOHTTP_AVAILABLE', False)

        with pytest.raises(ImportError, match="aiohttp required"):
            VLLMClientAdapter(vllm_url="http://localhost:8000")
