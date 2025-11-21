"""Unit tests for core.memory DTOs and basic components

Quick win tests for LlmCallDTO and LlmResponseDTO dataclasses.
"""

import pytest
from core.memory.dtos.llm_call_dto import LlmCallDTO
from core.memory.dtos.llm_response_dto import LlmResponseDTO


class TestLlmCallDTO:
    """Test LlmCallDTO dataclass"""

    def test_llm_call_dto_creation(self):
        """Test creating LlmCallDTO with all fields."""
        dto = LlmCallDTO(
            session_id="session-001",
            task_id="task-001",
            requester="user:123",
            model="gpt-4",
            params={"temperature": 0.7, "top_p": 0.9},
            content="Generate code for API endpoint",
            parent_msg_id="msg-001",
        )

        assert dto.session_id == "session-001"
        assert dto.task_id == "task-001"
        assert dto.requester == "user:123"
        assert dto.model == "gpt-4"
        assert dto.params == {"temperature": 0.7, "top_p": 0.9}
        assert dto.content == "Generate code for API endpoint"
        assert dto.parent_msg_id == "msg-001"

    def test_llm_call_dto_without_parent(self):
        """Test LlmCallDTO without parent_msg_id."""
        dto = LlmCallDTO(
            session_id="session-002",
            task_id="task-002",
            requester="agent:devops-1",
            model="llama-2",
            params={"temperature": 0.5},
            content="Deploy application",
        )

        assert dto.parent_msg_id is None
        assert dto.requester == "agent:devops-1"

    def test_llm_call_dto_empty_params(self):
        """Test LlmCallDTO with empty params dict."""
        dto = LlmCallDTO(
            session_id="session-003",
            task_id="task-003",
            requester="user:456",
            model="qwen",
            params={},
            content="Simple prompt",
        )

        assert dto.params == {}

    def test_llm_call_dto_frozen(self):
        """Test LlmCallDTO is immutable (frozen)."""
        dto = LlmCallDTO(
            session_id="session-004",
            task_id="task-004",
            requester="user:789",
            model="claude",
            params={},
            content="Test",
        )

        with pytest.raises(AttributeError):
            dto.session_id = "new-session"

    def test_llm_call_dto_equality(self):
        """Test LlmCallDTO equality comparison."""
        dto1 = LlmCallDTO(
            session_id="session-005",
            task_id="task-005",
            requester="user:001",
            model="gpt-4",
            params={"temp": 0.7},
            content="Prompt 1",
        )

        dto2 = LlmCallDTO(
            session_id="session-005",
            task_id="task-005",
            requester="user:001",
            model="gpt-4",
            params={"temp": 0.7},
            content="Prompt 1",
        )

        assert dto1 == dto2

    def test_llm_call_dto_different_instances(self):
        """Test LlmCallDTO inequality."""
        dto1 = LlmCallDTO(
            session_id="session-006",
            task_id="task-006",
            requester="user:001",
            model="gpt-4",
            params={},
            content="Prompt",
        )

        dto2 = LlmCallDTO(
            session_id="session-007",
            task_id="task-007",
            requester="user:002",
            model="gpt-3",
            params={},
            content="Different",
        )

        assert dto1 != dto2

    def test_llm_call_dto_with_complex_params(self):
        """Test LlmCallDTO with complex nested params."""
        params = {
            "temperature": 0.8,
            "stop": ["END", "---"],
            "seed": 42,
            "nested": {"key": "value"},
        }
        dto = LlmCallDTO(
            session_id="session-008",
            task_id="task-008",
            requester="agent:qa-1",
            model="mistral",
            params=params,
            content="Test prompt",
        )

        assert dto.params["stop"] == ["END", "---"]
        assert dto.params["nested"]["key"] == "value"


class TestLlmResponseDTO:
    """Test LlmResponseDTO dataclass"""

    def test_llm_response_dto_creation(self):
        """Test creating LlmResponseDTO with all fields."""
        dto = LlmResponseDTO(
            session_id="session-001",
            task_id="task-001",
            responder="agent:dev-1",
            model="gpt-4",
            content="Here is the generated code...",
            usage={"tokens": 150, "latency_ms": 2500},
            parent_msg_id="msg-001",
        )

        assert dto.session_id == "session-001"
        assert dto.task_id == "task-001"
        assert dto.responder == "agent:dev-1"
        assert dto.model == "gpt-4"
        assert dto.content == "Here is the generated code..."
        assert dto.usage == {"tokens": 150, "latency_ms": 2500}
        assert dto.parent_msg_id == "msg-001"

    def test_llm_response_dto_without_parent(self):
        """Test LlmResponseDTO without parent_msg_id."""
        dto = LlmResponseDTO(
            session_id="session-002",
            task_id="task-002",
            responder="model:qwen3-coder",
            model="qwen",
            content="Response content",
            usage={"tokens": 200, "latency_ms": 1800},
        )

        assert dto.parent_msg_id is None
        assert dto.responder == "model:qwen3-coder"

    def test_llm_response_dto_empty_content(self):
        """Test LlmResponseDTO with empty content."""
        dto = LlmResponseDTO(
            session_id="session-003",
            task_id="task-003",
            responder="agent:test",
            model="test-model",
            content="",
            usage={"tokens": 0},
        )

        assert dto.content == ""
        assert dto.usage["tokens"] == 0

    def test_llm_response_dto_frozen(self):
        """Test LlmResponseDTO is immutable (frozen)."""
        dto = LlmResponseDTO(
            session_id="session-004",
            task_id="task-004",
            responder="agent:dev",
            model="gpt-4",
            content="Test",
            usage={},
        )

        with pytest.raises(AttributeError):
            dto.session_id = "new-session"

    def test_llm_response_dto_equality(self):
        """Test LlmResponseDTO equality comparison."""
        dto1 = LlmResponseDTO(
            session_id="session-005",
            task_id="task-005",
            responder="agent:qa",
            model="claude",
            content="Response 1",
            usage={"tokens": 100},
        )

        dto2 = LlmResponseDTO(
            session_id="session-005",
            task_id="task-005",
            responder="agent:qa",
            model="claude",
            content="Response 1",
            usage={"tokens": 100},
        )

        assert dto1 == dto2

    def test_llm_response_dto_inequality(self):
        """Test LlmResponseDTO inequality."""
        dto1 = LlmResponseDTO(
            session_id="session-006",
            task_id="task-006",
            responder="agent:dev",
            model="gpt-4",
            content="Response A",
            usage={"tokens": 150},
        )

        dto2 = LlmResponseDTO(
            session_id="session-007",
            task_id="task-007",
            responder="agent:qa",
            model="gpt-3",
            content="Response B",
            usage={"tokens": 200},
        )

        assert dto1 != dto2

    def test_llm_response_dto_with_detailed_usage(self):
        """Test LlmResponseDTO with detailed usage metrics."""
        usage = {
            "tokens": 1500,
            "latency_ms": 3200,
            "cache_hits": 5,
            "retries": 0,
        }
        dto = LlmResponseDTO(
            session_id="session-008",
            task_id="task-008",
            responder="agent:performance",
            model="gpt-4-turbo",
            content="Detailed response",
            usage=usage,
        )

        assert dto.usage["cache_hits"] == 5
        assert dto.usage["retries"] == 0
        assert len(dto.usage) == 4

    def test_llm_response_dto_long_content(self):
        """Test LlmResponseDTO with long content."""
        long_content = "Generated code:\n" * 100
        dto = LlmResponseDTO(
            session_id="session-009",
            task_id="task-009",
            responder="agent:dev",
            model="gpt-4",
            content=long_content,
            usage={"tokens": 5000},
        )

        assert len(dto.content) > 1000
        assert dto.content.startswith("Generated code:")


class TestMemoryDTOsIntegration:
    """Integration tests for memory DTOs together"""

    def test_call_and_response_pairing(self):
        """Test creating matching call and response DTOs."""
        call = LlmCallDTO(
            session_id="session-010",
            task_id="task-010",
            requester="user:admin",
            model="gpt-4",
            params={"temperature": 0.7},
            content="Generate SQL query",
            parent_msg_id=None,
        )

        response = LlmResponseDTO(
            session_id="session-010",
            task_id="task-010",
            responder="model:gpt-4",
            model="gpt-4",
            content="SELECT * FROM users...",
            usage={"tokens": 250},
            parent_msg_id=None,
        )

        # Verify they're related
        assert call.session_id == response.session_id
        assert call.task_id == response.task_id
        assert call.model == response.model

    def test_multiple_dtos_in_conversation(self):
        """Test simulating a multi-turn conversation."""
        call1 = LlmCallDTO(
            session_id="conv-001",
            task_id="task-001",
            requester="user:123",
            model="gpt-4",
            params={},
            content="Hello",
        )

        response1 = LlmResponseDTO(
            session_id="conv-001",
            task_id="task-001",
            responder="model:gpt-4",
            model="gpt-4",
            content="Hello! How can I help?",
            usage={"tokens": 50},
            parent_msg_id=None,
        )

        call2 = LlmCallDTO(
            session_id="conv-001",
            task_id="task-002",
            requester="user:123",
            model="gpt-4",
            params={},
            content="Generate code",
            parent_msg_id="msg-1",
        )

        response2 = LlmResponseDTO(
            session_id="conv-001",
            task_id="task-002",
            responder="model:gpt-4",
            model="gpt-4",
            content="def hello(): pass",
            usage={"tokens": 100},
            parent_msg_id="msg-1",
        )

        # Verify conversation flow
        assert call2.parent_msg_id == "msg-1"
        assert response2.parent_msg_id == "msg-1"
        assert call1.parent_msg_id is None
        assert response1.parent_msg_id is None
