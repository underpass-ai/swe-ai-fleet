"""Unit tests for VLLMRequest domain model."""

import pytest
from core.ray_jobs.domain import Message, VLLMRequest


class TestMessage:
    """Tests for Message value object."""

    def test_message_creation(self):
        """Test creating a Message."""
        # Act
        message = Message(role="system", content="You are a helpful assistant")

        # Assert
        assert message.role == "system"
        assert message.content == "You are a helpful assistant"

    def test_message_to_dict(self):
        """Test converting Message to dict."""
        # Arrange
        message = Message(role="user", content="Hello")

        # Act
        result = message.to_dict()

        # Assert
        assert result == {"role": "user", "content": "Hello"}


class TestVLLMRequest:
    """Tests for VLLMRequest domain model."""

    def test_create_factory_method(self):
        """Test creating VLLMRequest using factory method."""
        # Act
        request = VLLMRequest.create(
            model="test-model",
            system_prompt="You are a helpful assistant",
            user_prompt="Write a test",
            temperature=0.7,
            max_tokens=1024,
        )

        # Assert
        assert request.model == "test-model"
        assert request.temperature == pytest.approx(0.7)
        assert request.max_tokens == 1024
        assert len(request.messages) == 2
        assert request.messages[0].role == "system"
        assert request.messages[0].content == "You are a helpful assistant"
        assert request.messages[1].role == "user"
        assert request.messages[1].content == "Write a test"

    def test_create_with_structured_outputs(self):
        """Test creating VLLMRequest with structured outputs."""
        # Arrange
        json_schema = {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        }

        # Act
        request = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            json_schema=json_schema,
            task_type="TASK_EXTRACTION",
        )

        # Assert
        assert request.json_schema == json_schema
        assert request.task_type == "TASK_EXTRACTION"

    def test_to_dict_basic(self):
        """Test converting VLLMRequest to dict without structured outputs."""
        # Arrange
        request = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            temperature=0.7,
            max_tokens=1024,
        )

        # Act
        result = request.to_dict()

        # Assert
        assert result["model"] == "test-model"
        assert result["temperature"] == pytest.approx(0.7)
        assert result["max_tokens"] == 1024
        assert len(result["messages"]) == 2
        assert "response_format" not in result

    def test_to_dict_with_structured_outputs(self):
        """Test converting VLLMRequest to dict with structured outputs."""
        # Arrange
        json_schema = {
            "type": "object",
            "properties": {
                "tasks": {"type": "array"}
            }
        }

        request = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            json_schema=json_schema,
            task_type="TASK_EXTRACTION",
        )

        # Act
        result = request.to_dict()

        # Assert
        assert "response_format" in result
        assert result["response_format"]["type"] == "json_schema"
        assert result["response_format"]["json_schema"]["name"] == "TASK_EXTRACTION"
        assert result["response_format"]["json_schema"]["schema"] == json_schema
        assert result["response_format"]["json_schema"]["strict"] is True

    def test_to_dict_with_structured_outputs_no_task_type(self):
        """Test structured outputs with no task_type uses default name."""
        # Arrange
        json_schema = {"type": "object"}

        request = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            json_schema=json_schema,
        )

        # Act
        result = request.to_dict()

        # Assert
        assert result["response_format"]["json_schema"]["name"] == "structured_output"

    def test_with_temperature(self):
        """Test creating new request with different temperature."""
        # Arrange
        original = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            temperature=0.7,
            max_tokens=1024,
        )

        # Act
        new_request = original.with_temperature(0.9)

        # Assert
        assert new_request.temperature == pytest.approx(0.9)
        assert new_request.model == original.model
        assert new_request.messages == original.messages
        assert new_request.max_tokens == original.max_tokens
        # Original unchanged (immutability)
        assert original.temperature == pytest.approx(0.7)

    def test_with_diversity(self):
        """Test creating new request with diversity factor."""
        # Arrange
        original = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            temperature=0.7,
            max_tokens=1024,
        )

        # Act
        new_request = original.with_diversity(1.3)

        # Assert
        assert new_request.temperature == pytest.approx(0.7 * 1.3)
        assert original.temperature == pytest.approx(0.7)  # Original unchanged

    def test_with_diversity_default_factor(self):
        """Test with_diversity uses default factor of 1.3."""
        # Arrange
        original = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            temperature=0.7,
            max_tokens=1024,
        )

        # Act
        new_request = original.with_diversity()

        # Assert
        assert new_request.temperature == pytest.approx(0.7 * 1.3)

    def test_with_structured_outputs(self):
        """Test creating new request with structured outputs."""
        # Arrange
        original = VLLMRequest.create(
            model="test-model",
            system_prompt="System",
            user_prompt="User",
            temperature=0.7,
            max_tokens=1024,
        )

        json_schema = {"type": "object"}

        # Act
        new_request = original.with_structured_outputs(json_schema, "TASK_EXTRACTION")

        # Assert
        assert new_request.json_schema == json_schema
        assert new_request.task_type == "TASK_EXTRACTION"
        assert new_request.model == original.model
        assert new_request.messages == original.messages
        assert new_request.temperature == pytest.approx(original.temperature)
        # Original unchanged
        assert original.json_schema is None
        assert original.task_type is None
