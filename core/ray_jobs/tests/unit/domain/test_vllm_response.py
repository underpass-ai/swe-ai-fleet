"""Unit tests for VLLMResponse domain model."""

import pytest
from core.ray_jobs.domain import VLLMResponse


class TestVLLMResponse:
    """Tests for VLLMResponse domain model."""

    def test_from_vllm_api_success(self):
        """Test creating VLLMResponse from vLLM API data."""
        # Arrange
        api_data = {
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

        # Act
        response = VLLMResponse.from_vllm_api(
            api_data=api_data,
            agent_id="agent-001",
            role="ARCHITECT",
            model="test-model",
            temperature=0.7,
        )

        # Assert
        assert response.content == "Generated text content"
        assert response.author_id == "agent-001"
        assert response.author_role == "ARCHITECT"
        assert response.model == "test-model"
        assert response.temperature == pytest.approx(0.7)
        assert response.tokens == 150
        assert response.reasoning is None

    def test_from_vllm_api_with_reasoning_field(self):
        """Test creating VLLMResponse with reasoning field in API data."""
        # Arrange
        api_data = {
            "choices": [
                {
                    "message": {
                        "content": "Generated text",
                        "reasoning": "This is the reasoning trace"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        # Act
        response = VLLMResponse.from_vllm_api(
            api_data=api_data,
            agent_id="agent-001",
            role="ARCHITECT",
            model="test-model",
            temperature=0.7,
        )

        # Assert
        assert response.reasoning == "This is the reasoning trace"

    def test_from_vllm_api_with_reasoning_parameter(self):
        """Test creating VLLMResponse with reasoning parameter."""
        # Arrange
        api_data = {
            "choices": [
                {
                    "message": {
                        "content": "Generated text"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        # Act
        response = VLLMResponse.from_vllm_api(
            api_data=api_data,
            agent_id="agent-001",
            role="ARCHITECT",
            model="test-model",
            temperature=0.7,
            reasoning="Reasoning from parameter",
        )

        # Assert
        assert response.reasoning == "Reasoning from parameter"

    def test_from_vllm_api_reasoning_parameter_overrides_api(self):
        """Test that reasoning parameter takes precedence over API field."""
        # Arrange
        api_data = {
            "choices": [
                {
                    "message": {
                        "content": "Generated text",
                        "reasoning": "API reasoning"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        # Act
        response = VLLMResponse.from_vllm_api(
            api_data=api_data,
            agent_id="agent-001",
            role="ARCHITECT",
            model="test-model",
            temperature=0.7,
            reasoning="Parameter reasoning",
        )

        # Assert
        assert response.reasoning == "Parameter reasoning"

    def test_from_vllm_api_strips_content(self):
        """Test that content is stripped of whitespace."""
        # Arrange
        api_data = {
            "choices": [
                {
                    "message": {
                        "content": "  Generated text  \n"
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        # Act
        response = VLLMResponse.from_vllm_api(
            api_data=api_data,
            agent_id="agent-001",
            role="ARCHITECT",
            model="test-model",
            temperature=0.7,
        )

        # Assert
        assert response.content == "Generated text"

    def test_from_vllm_api_no_usage(self):
        """Test handling when usage data is missing."""
        # Arrange
        api_data = {
            "choices": [
                {
                    "message": {
                        "content": "Generated text"
                    }
                }
            ]
        }

        # Act
        response = VLLMResponse.from_vllm_api(
            api_data=api_data,
            agent_id="agent-001",
            role="ARCHITECT",
            model="test-model",
            temperature=0.7,
        )

        # Assert
        assert response.tokens == 0

    def test_from_vllm_api_invalid_structure_missing_choices(self):
        """Test that KeyError is raised for invalid API structure."""
        # Arrange
        api_data = {
            "usage": {
                "total_tokens": 150
            }
        }

        # Act & Assert
        with pytest.raises(KeyError, match="Invalid vLLM API response structure"):
            VLLMResponse.from_vllm_api(
                api_data=api_data,
                agent_id="agent-001",
                role="ARCHITECT",
                model="test-model",
                temperature=0.7,
            )

    def test_from_vllm_api_invalid_structure_empty_choices(self):
        """Test that KeyError is raised for empty choices array."""
        # Arrange
        api_data = {
            "choices": [],
            "usage": {
                "total_tokens": 150
            }
        }

        # Act & Assert
        with pytest.raises(KeyError, match="Invalid vLLM API response structure"):
            VLLMResponse.from_vllm_api(
                api_data=api_data,
                agent_id="agent-001",
                role="ARCHITECT",
                model="test-model",
                temperature=0.7,
            )

    def test_from_vllm_api_invalid_structure_missing_message(self):
        """Test that KeyError is raised when message is missing."""
        # Arrange
        api_data = {
            "choices": [
                {}
            ],
            "usage": {
                "total_tokens": 150
            }
        }

        # Act & Assert
        with pytest.raises(KeyError, match="Invalid vLLM API response structure"):
            VLLMResponse.from_vllm_api(
                api_data=api_data,
                agent_id="agent-001",
                role="ARCHITECT",
                model="test-model",
                temperature=0.7,
            )

    def test_to_dict_basic(self):
        """Test converting VLLMResponse to dict without reasoning."""
        # Arrange
        response = VLLMResponse(
            content="Generated text",
            author_id="agent-001",
            author_role="ARCHITECT",
            model="test-model",
            temperature=0.7,
            tokens=150,
        )

        # Act
        result = response.to_dict()

        # Assert
        assert result["content"] == "Generated text"
        assert result["author_id"] == "agent-001"
        assert result["author_role"] == "ARCHITECT"
        assert result["model"] == "test-model"
        assert result["temperature"] == pytest.approx(0.7)
        assert result["tokens"] == 150
        assert "reasoning" not in result

    def test_to_dict_with_reasoning(self):
        """Test converting VLLMResponse to dict with reasoning."""
        # Arrange
        response = VLLMResponse(
            content="Generated text",
            author_id="agent-001",
            author_role="ARCHITECT",
            model="test-model",
            temperature=0.7,
            tokens=150,
            reasoning="Reasoning trace",
        )

        # Act
        result = response.to_dict()

        # Assert
        assert result["reasoning"] == "Reasoning trace"
