"""Tests for GenerateNextActionUseCase."""

import json
import pytest
from unittest.mock import AsyncMock

from core.agents.application.usecases.generate_next_action_usecase import GenerateNextActionUseCase


class TestGenerateNextActionUseCase:
    """Test suite for GenerateNextActionUseCase."""

    @pytest.fixture
    def llm_client(self):
        """Create a mock LLM client."""
        return AsyncMock()

    @pytest.fixture
    def usecase(self, llm_client):
        """Create a GenerateNextActionUseCase instance."""
        return GenerateNextActionUseCase(llm_client)

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

    @pytest.fixture
    def observation_history(self):
        """Create sample observation history."""
        return [
            {
                "iteration": 1,
                "action": "files.read_file('src/file.py')",
                "success": True,
                "observations": "Found the file"
            },
            {
                "iteration": 2,
                "action": "git.status()",
                "success": True,
                "observations": "Clean working tree"
            }
        ]

    @pytest.mark.asyncio
    async def test_execute_continue_action(self, usecase, llm_client, available_tools, observation_history):
        """Test decision to continue with next action."""
        response_data = {
            "done": False,
            "reasoning": "Need to read more files",
            "step": {
                "tool": "files",
                "operation": "read_file",
                "params": {"path": "src/other.py"}
            }
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        result = await usecase.execute(
            task="Implement feature",
            context="Project structure",
            observation_history=observation_history,
            available_tools=available_tools
        )

        # Assert
        assert result["done"] is False
        assert result["reasoning"] == "Need to read more files"
        assert result["step"]["tool"] == "files"

    @pytest.mark.asyncio
    async def test_execute_task_complete(self, usecase, llm_client, available_tools, observation_history):
        """Test decision that task is complete."""
        response_data = {
            "done": True,
            "reasoning": "All files processed successfully",
            "step": None
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        result = await usecase.execute(
            task="Implement feature",
            context="Project structure",
            observation_history=observation_history,
            available_tools=available_tools
        )

        # Assert
        assert result["done"] is True
        assert "successfully" in result["reasoning"]
        assert result.get("step") is None

    @pytest.mark.asyncio
    async def test_execute_with_empty_history(self, usecase, llm_client, available_tools):
        """Test decision making with empty observation history."""
        response_data = {
            "done": False,
            "reasoning": "Starting task",
            "step": {
                "tool": "files",
                "operation": "list_files",
                "params": {"path": ".", "recursive": False}
            }
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        result = await usecase.execute(
            task="Implement feature",
            context="Project structure",
            observation_history=[],
            available_tools=available_tools
        )

        # Assert
        assert result["done"] is False
        assert result["step"]["operation"] == "list_files"

    @pytest.mark.asyncio
    async def test_execute_with_markdown_wrapper(self, usecase, llm_client, available_tools, observation_history):
        """Test parsing markdown-wrapped response."""
        response_data = {
            "done": False,
            "reasoning": "Continue",
            "step": {"tool": "tests", "operation": "pytest", "params": {"path": "tests/"}}
        }
        wrapped_response = f"```json\n{json.dumps(response_data)}\n```"
        llm_client.generate = AsyncMock(return_value=wrapped_response)

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            observation_history=observation_history,
            available_tools=available_tools
        )

        # Assert
        assert result["done"] is False
        assert result["step"]["tool"] == "tests"

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json(self, usecase, llm_client, available_tools, observation_history):
        """Test handling of invalid JSON response."""
        llm_client.generate = AsyncMock(return_value="Invalid JSON")

        # Execute
        result = await usecase.execute(
            task="Test task",
            context="Test context",
            observation_history=observation_history,
            available_tools=available_tools
        )

        # Assert - should return done=True as fallback
        assert result["done"] is True
        assert "Failed to parse LLM response" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_execute_includes_last_observations(self, usecase, llm_client, available_tools):
        """Test that last 5 observations are included in prompt."""
        history = [{"iteration": i, "action": f"action_{i}", "success": True} for i in range(10)]

        response_data = {"done": True, "reasoning": "Complete"}
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        await usecase.execute(
            task="Test task",
            context="Test context",
            observation_history=history,
            available_tools=available_tools
        )

        # Assert - should only include last 5 (iterations 5-9)
        call_args = llm_client.generate.call_args
        user_prompt = call_args[0][1]
        # Should include observation from iteration 5 (not 0)
        assert "Iteration 5" in user_prompt
        assert "Iteration 0" not in user_prompt

