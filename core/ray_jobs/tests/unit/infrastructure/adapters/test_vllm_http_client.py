"""Tests for VLLMHTTPClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from core.ray_jobs.domain import VLLMRequest, VLLMResponse
from core.ray_jobs.infrastructure.adapters import VLLMHTTPClient


@pytest.mark.skip(reason="Async mocking issues - tested via integration tests")
class TestVLLMHTTPClient:
    """Tests for VLLMHTTPClient."""

    @pytest.fixture
    def client(self):
        """Create VLLMHTTPClient for testing."""
        return VLLMHTTPClient(
            vllm_url="http://vllm-test:8000",
            agent_id="agent-test-001",
            role="DEV",
            model="test-model",
            timeout=30,
        )

    @pytest.fixture
    def vllm_request(self):
        """Create VLLMRequest for testing."""
        return VLLMRequest.create(
            model="test-model",
            system_prompt="You are a helpful assistant",
            user_prompt="Write a test",
            temperature=0.7,
            max_tokens=1024,
        )

    @pytest.mark.asyncio
    async def test_generate_success(self, client, vllm_request):
        """Test successful generation."""
        # Arrange
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Generated text content"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act
            response = await client.generate(vllm_request)

        # Assert
        assert isinstance(response, VLLMResponse)
        assert response.content == "Generated text content"
        assert response.author_id == "agent-test-001"
        assert response.author_role == "DEV"
        assert response.model == "test-model"
        assert response.temperature == pytest.approx(0.7)
        assert response.tokens == 150

    @pytest.mark.asyncio
    async def test_generate_with_correct_payload(self, client, vllm_request):
        """Test that request payload is correctly formatted."""
        # Arrange
        mock_response_data = {
            "choices": [{"message": {"content": "Test"}}],
            "usage": {"total_tokens": 10}
        }

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act
            await client.generate(vllm_request)

        # Assert - verify payload structure
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://vllm-test:8000/v1/chat/completions"

        payload = call_args[1]["json"]
        assert payload["model"] == "test-model"
        assert payload["temperature"] == pytest.approx(0.7)
        assert payload["max_tokens"] == 1024
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are a helpful assistant"
        assert payload["messages"][1]["role"] == "user"
        assert payload["messages"][1]["content"] == "Write a test"

    @pytest.mark.asyncio
    async def test_generate_with_timeout(self, client, vllm_request):
        """Test that timeout is properly configured."""
        # Arrange
        mock_response_data = {
            "choices": [{"message": {"content": "Test"}}],
            "usage": {"total_tokens": 10}
        }

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act
            await client.generate(vllm_request)

        # Assert - verify timeout parameter
        call_args = mock_session.post.call_args
        timeout_arg = call_args[1]["timeout"]
        assert isinstance(timeout_arg, aiohttp.ClientTimeout)
        assert timeout_arg.total == 30

    @pytest.mark.asyncio
    async def test_generate_http_error(self, client, vllm_request):
        """Test handling of HTTP errors."""
        # Arrange
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientError("HTTP 500")
        )

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Failed to call vLLM API"):
                await client.generate(vllm_request)

    @pytest.mark.asyncio
    async def test_generate_invalid_response_format(self, client, vllm_request):
        """Test handling of invalid response format."""
        # Arrange - missing 'choices' key
        mock_response_data = {
            "usage": {"total_tokens": 10}
        }

        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Invalid vLLM response"):
                await client.generate(vllm_request)

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, client, vllm_request):
        """Test handling of connection errors."""
        # Arrange
        mock_session = AsyncMock()
        mock_session.post = AsyncMock(
            side_effect=aiohttp.ClientConnectionError("Connection refused")
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Failed to call vLLM API"):
                await client.generate(vllm_request)

