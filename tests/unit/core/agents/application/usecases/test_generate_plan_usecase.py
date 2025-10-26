"""Tests for GeneratePlanUseCase."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase


class TestGeneratePlanUseCase:
    """Test suite for GeneratePlanUseCase."""

    @pytest.fixture
    def llm_client(self):
        """Create a mock LLM client."""
        return AsyncMock()

    @pytest.fixture
    def usecase(self, llm_client):
        """Create a GeneratePlanUseCase instance."""
        return GeneratePlanUseCase(llm_client)

    @pytest.fixture
    def available_tools(self):
        """Create sample available tools dict."""
        return {
            "capabilities": [
                "files: read_file, write_file",
                "git: status, commit"
            ],
            "mode": "full"
        }

    @pytest.mark.asyncio
    async def test_execute_success(self, usecase, llm_client, available_tools):
        """Test successful plan generation."""
        # Setup mock LLM response
        response_data = {
            "reasoning": "We need to implement authentication",
            "steps": [
                {"tool": "files", "operation": "read_file", "params": {"path": "src/auth.py"}},
                {"tool": "tests", "operation": "pytest", "params": {"path": "tests/test_auth.py"}}
            ]
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        result = await usecase.execute(
            task="Add JWT authentication",
            context="Project uses Python 3.13",
            role="DEV",
            available_tools=available_tools,
            constraints=None
        )

        # Assert
        assert result["reasoning"] == "We need to implement authentication"
        assert len(result["steps"]) == 2
        assert result["steps"][0]["tool"] == "files"
        assert llm_client.generate.called

    @pytest.mark.asyncio
    async def test_execute_with_markdown_wrapper(self, usecase, llm_client, available_tools):
        """Test parsing response wrapped in markdown code block."""
        response_data = {
            "reasoning": "Test reasoning",
            "steps": [{"tool": "files", "operation": "list_files", "params": {"path": "."}}]
        }
        # Simulate markdown-wrapped response
        wrapped_response = f"```json\n{json.dumps(response_data)}\n```"
        llm_client.generate = AsyncMock(return_value=wrapped_response)

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            role="DEV",
            available_tools=available_tools
        )

        # Assert
        assert result["reasoning"] == "Test reasoning"
        assert len(result["steps"]) == 1

    @pytest.mark.asyncio
    async def test_execute_with_plain_code_block(self, usecase, llm_client, available_tools):
        """Test parsing response wrapped in plain code block."""
        response_data = {
            "reasoning": "Test reasoning",
            "steps": [{"tool": "git", "operation": "status", "params": {}}]
        }
        # Simulate plain code block
        wrapped_response = f"```\n{json.dumps(response_data)}\n```"
        llm_client.generate = AsyncMock(return_value=wrapped_response)

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            role="DEV",
            available_tools=available_tools
        )

        # Assert
        assert len(result["steps"]) == 1

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json(self, usecase, llm_client, available_tools):
        """Test handling of invalid JSON response."""
        llm_client.generate = AsyncMock(return_value="Invalid JSON response")

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            role="DEV",
            available_tools=available_tools
        )

        # Assert - should return fallback plan
        assert result["reasoning"] == "Failed to parse LLM response, using fallback"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["tool"] == "files"

    @pytest.mark.asyncio
    async def test_execute_with_missing_steps(self, usecase, llm_client, available_tools):
        """Test handling of response missing 'steps' field."""
        llm_client.generate = AsyncMock(return_value=json.dumps({"reasoning": "Test"}))

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            role="DEV",
            available_tools=available_tools
        )

        # Assert - should return fallback plan
        assert "Failed to parse LLM response" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_execute_with_custom_role(self, usecase, llm_client, available_tools):
        """Test plan generation for QA role."""
        response_data = {
            "reasoning": "Need to create tests",
            "steps": [{"tool": "tests", "operation": "pytest", "params": {"path": "tests/"}}]
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        result = await usecase.execute(
            task="Create test coverage",
            context="Project has auth module",
            role="QA",
            available_tools=available_tools
        )

        # Assert
        assert llm_client.generate.called
        call_args = llm_client.generate.call_args
        # System prompt should contain QA role
        assert "QA" in call_args[0][0] or "testing" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_execute_with_constraints(self, usecase, llm_client, available_tools):
        """Test plan generation with constraints."""
        response_data = {
            "reasoning": "Constrained plan",
            "steps": [{"tool": "files", "operation": "read_file", "params": {"path": "src/file.py"}}]
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))
        constraints = {"max_operations": 5, "iterative": True}

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            role="DEV",
            available_tools=available_tools,
            constraints=constraints
        )

        # Assert
        assert len(result["steps"]) == 1

