"""Tests for VLLMHTTPClient."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from core.ray_jobs.domain import VLLMRequest, VLLMResponse
from core.ray_jobs.infrastructure.adapters import VLLMHTTPClient


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

    def _create_mock_response(
        self,
        response_data: dict,
        status: int = 200,
        raise_for_status_side_effect=None,
    ) -> AsyncMock:
        """Create a mock aiohttp response with async context manager support."""
        mock_response = AsyncMock()
        mock_response.status = status
        mock_response.json = AsyncMock(return_value=response_data)
        if raise_for_status_side_effect:
            mock_response.raise_for_status = MagicMock(side_effect=raise_for_status_side_effect)
        else:
            mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        return mock_response

    def _create_mock_session(
        self,
        mock_response: AsyncMock,
        post_side_effect=None,
        post_context_side_effect=None,
    ) -> AsyncMock:
        """Create a mock aiohttp session with async context manager support."""
        mock_session = AsyncMock()
        if post_context_side_effect:
            # Special case: post() returns a context manager that raises on __aenter__
            mock_post_context = AsyncMock()
            mock_post_context.__aenter__ = AsyncMock(side_effect=post_context_side_effect)
            mock_session.post = MagicMock(return_value=mock_post_context)
        elif post_side_effect:
            mock_session.post = MagicMock(side_effect=post_side_effect)
        else:
            mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    def _patch_client_session(self, mock_session: AsyncMock):
        """Create a patch context for aiohttp.ClientSession."""
        return patch("aiohttp.ClientSession", return_value=mock_session)

    def _create_json_schema_fixture(self) -> dict:
        """Create a standard JSON schema for task extraction testing."""
        return {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        }

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

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)
        # post() returns an async context manager
        mock_post_context = AsyncMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.post = MagicMock(return_value=mock_post_context)

        with self._patch_client_session(mock_session):
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

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        mock_client_session = MagicMock(return_value=mock_session)
        with patch("aiohttp.ClientSession", mock_client_session):
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

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        mock_client_session = MagicMock(return_value=mock_session)
        with patch("aiohttp.ClientSession", mock_client_session):
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
        mock_response = self._create_mock_response(
            {},
            raise_for_status_side_effect=aiohttp.ClientError("HTTP 500")
        )
        mock_session = self._create_mock_session(mock_response)

        with self._patch_client_session(mock_session):
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

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        mock_client_session = MagicMock(return_value=mock_session)
        with patch("aiohttp.ClientSession", mock_client_session):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Invalid vLLM response"):
                await client.generate(vllm_request)

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, client, vllm_request):
        """Test handling of connection errors."""
        # Arrange
        mock_response = self._create_mock_response({})
        mock_session = self._create_mock_session(
            mock_response,
            post_context_side_effect=aiohttp.ClientConnectionError("Connection refused")
        )

        mock_client_session = MagicMock(return_value=mock_session)
        with patch("aiohttp.ClientSession", mock_client_session):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Failed to call vLLM API"):
                await client.generate(vllm_request)

    @pytest.mark.asyncio
    async def test_generate_with_reasoning_field(self, client, vllm_request):
        """Test handling of reasoning field in response."""
        # Arrange
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Generated text content",
                        "reasoning": "This is the reasoning trace"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        with self._patch_client_session(mock_session):
            # Act
            response = await client.generate(vllm_request)

        # Assert
        assert response.reasoning == "This is the reasoning trace"

    @pytest.mark.asyncio
    async def test_generate_with_think_tags_fallback(self, client, vllm_request):
        """Test extraction of reasoning from <think> tags when reasoning field is missing."""
        # Arrange
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "<think>This is reasoning</think>Generated text content"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        with self._patch_client_session(mock_session):
            # Act
            response = await client.generate(vllm_request)

        # Assert
        assert response.reasoning == "This is reasoning"
        assert "<think>" not in response.content.lower()
        assert "Generated text content" in response.content

    @pytest.mark.asyncio
    async def test_generate_with_structured_outputs_valid_json(self, client):
        """Test structured outputs with valid JSON."""
        # Arrange
        json_schema = self._create_json_schema_fixture()

        vllm_request = VLLMRequest.create(
            model="test-model",
            system_prompt="You are a helpful assistant",
            user_prompt="Extract tasks",
            temperature=0.7,
            max_tokens=1024,
            json_schema=json_schema,
            task_type="TASK_EXTRACTION",
        )

        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": '{"tasks": [{"title": "Task 1"}]}'
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        with self._patch_client_session(mock_session):
            # Act
            response = await client.generate(vllm_request)

        # Assert
        assert isinstance(response, VLLMResponse)
        # Verify JSON is valid
        import json
        parsed_json = json.loads(response.content)
        assert "tasks" in parsed_json
        assert len(parsed_json["tasks"]) == 1

    @pytest.mark.asyncio
    async def test_generate_with_structured_outputs_invalid_json(self, client):
        """Test structured outputs with invalid JSON raises error."""
        # Arrange
        json_schema = self._create_json_schema_fixture()

        vllm_request = VLLMRequest.create(
            model="test-model",
            system_prompt="You are a helpful assistant",
            user_prompt="Extract tasks",
            temperature=0.7,
            max_tokens=1024,
            json_schema=json_schema,
            task_type="TASK_EXTRACTION",
        )

        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Invalid JSON content"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        with self._patch_client_session(mock_session):
            # Act & Assert
            with pytest.raises(RuntimeError, match="vLLM returned invalid JSON"):
                await client.generate(vllm_request)

    @pytest.mark.asyncio
    async def test_generate_with_structured_outputs_payload(self, client):
        """Test that structured outputs payload includes response_format."""
        # Arrange
        json_schema = {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array"
                }
            }
        }

        vllm_request = VLLMRequest.create(
            model="test-model",
            system_prompt="You are a helpful assistant",
            user_prompt="Extract tasks",
            temperature=0.7,
            max_tokens=1024,
            json_schema=json_schema,
            task_type="TASK_EXTRACTION",
        )

        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": '{"tasks": []}'
                    }
                }
            ],
            "usage": {
                "total_tokens": 10
            }
        }

        mock_response = self._create_mock_response(mock_response_data)
        mock_session = self._create_mock_session(mock_response)

        mock_client_session = MagicMock(return_value=mock_session)
        with patch("aiohttp.ClientSession", mock_client_session):
            # Act
            await client.generate(vllm_request)

        # Assert - verify payload includes response_format
        call_args = mock_session.post.call_args
        payload = call_args[1]["json"]
        assert "response_format" in payload
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["name"] == "TASK_EXTRACTION"
        assert payload["response_format"]["json_schema"]["strict"] is True

