"""Tests for GenerateNextActionUseCase."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.domain.entities import ExecutionStep, ObservationHistories
from core.agents_and_tools.common.domain.entities import (
    AgentCapabilities,
    Capability,
    CapabilityCollection,
    ExecutionMode,
    ExecutionModeEnum,
    ToolDefinition,
    ToolRegistry,
)


class TestGenerateNextActionUseCase:
    """Test suite for GenerateNextActionUseCase."""

    @pytest.fixture
    def llm_client(self):
        """Create a mock LLM client."""
        return AsyncMock()

    @pytest.fixture
    def prompt_loader(self):
        """Create a mock PromptLoader."""
        mock = MagicMock()
        mock.get_system_prompt_template.return_value = """You are an autonomous agent using ReAct (Reasoning + Acting) pattern.

  Available tools:
  {capabilities}

  Decide the next action based on task and previous observations.
  Respond in JSON format:
  {{
    "done": false,
    "reasoning": "Why this action...",
    "step": {{"tool": "files", "operation": "read_file", "params": {{"path": "..."}}}}
  }}

  Or if task is complete:
  {{
    "done": true,
    "reasoning": "Task complete because..."
  }}"""
        mock.get_user_prompt_template.return_value = """Task: {task}

  Context: {context}

  Observation History:
  {observation_history}

  What should I do next?"""
        return mock

    @pytest.fixture
    def json_parser(self):
        """Create a mock JSONResponseParser."""
        from core.agents_and_tools.agents.infrastructure.services.json_response_parser import (
            JSONResponseParser,
        )
        return JSONResponseParser()

    @pytest.fixture
    def step_mapper(self):
        """Create an ExecutionStepMapper."""
        from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import (
            ExecutionStepMapper,
        )
        return ExecutionStepMapper()

    @pytest.fixture
    def usecase(self, llm_client, prompt_loader, json_parser, step_mapper):
        """Create a GenerateNextActionUseCase instance with mocked dependencies."""
        return GenerateNextActionUseCase(
            llm_client=llm_client,
            prompt_loader=prompt_loader,
            json_parser=json_parser,
            step_mapper=step_mapper,
        )

    @pytest.fixture
    def available_tools(self):
        """Create sample available tools entity."""
        # Create tool definitions
        files_tool = ToolDefinition(
            name="files",
            operations={"operations": ["read_file", "write_file"]}
        )
        git_tool = ToolDefinition(
            name="git",
            operations={"operations": ["status", "commit"]}
        )

        # Create capabilities
        capabilities = [
            Capability(tool="files", operation="read_file"),
            Capability(tool="files", operation="write_file"),
            Capability(tool="git", operation="status"),
            Capability(tool="git", operation="commit"),
        ]

        return AgentCapabilities(
            tools=ToolRegistry.from_definitions([files_tool, git_tool]),
            mode=ExecutionMode(value=ExecutionModeEnum.FULL),
            operations=CapabilityCollection.from_list(capabilities),
            summary="Files and Git tools available for full operations"
        )

    @pytest.fixture
    def observation_history(self):
        """Create sample observation history."""
        history = ObservationHistories()

        # Add observations with ExecutionStep entities
        step1 = ExecutionStep(tool="files", operation="read_file", params={"path": "src/file.py"})
        history.add(
            iteration=1,
            action=step1,
            result="Found the file",
            success=True
        )

        step2 = ExecutionStep(tool="git", operation="status", params={})
        history.add(
            iteration=2,
            action=step2,
            result="Clean working tree",
            success=True
        )

        return history

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
        assert result.done is False
        assert result.reasoning == "Need to read more files"
        assert result.step.tool == "files"

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
        assert result.done is True
        assert "successfully" in result.reasoning
        assert result.step is None

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
            observation_history=ObservationHistories(),
            available_tools=available_tools
        )

        # Assert
        assert result.done is False
        assert result.step.operation == "list_files"

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
        assert result.done is False
        assert result.step.tool == "tests"

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json(self, usecase, llm_client, available_tools, observation_history):
        """Test handling of invalid JSON response."""
        llm_client.generate = AsyncMock(return_value="Invalid JSON")

        # Execute - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to parse JSON response"):
            await usecase.execute(
                task="Test task",
                context="Test context",
                observation_history=observation_history,
                available_tools=available_tools
            )

    @pytest.mark.asyncio
    async def test_execute_includes_last_observations(self, usecase, llm_client, available_tools):
        """Test that last 5 observations are included in prompt."""
        history = ObservationHistories()

        # Create 10 observations
        for i in range(10):
            step = ExecutionStep(tool="test", operation=f"action_{i}", params={})
            history.add(
                iteration=i,
                action=step,
                result=f"result_{i}",
                success=True
            )

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

