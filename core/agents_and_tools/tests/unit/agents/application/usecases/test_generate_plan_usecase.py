"""Tests for GeneratePlanUseCase."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.domain.entities.rbac.role_factory import RoleFactory
from core.agents_and_tools.common.domain.entities import (
    AgentCapabilities,
    Capability,
    CapabilityCollection,
    ExecutionMode,
    ExecutionModeEnum,
    ToolDefinition,
    ToolRegistry,
)


class TestGeneratePlanUseCase:
    """Test suite for GeneratePlanUseCase."""

    @pytest.fixture
    def dev_role(self):
        """Create a Developer role."""
        return RoleFactory.create_role_by_name("developer")

    @pytest.fixture
    def qa_role(self):
        """Create a QA role."""
        return RoleFactory.create_role_by_name("qa")

    @pytest.fixture
    def llm_client(self):
        """Create a mock LLM client."""
        return AsyncMock()

    @pytest.fixture
    def prompt_loader(self):
        """Create a mock PromptLoader."""
        mock = MagicMock()
        mock.load_prompt_config.return_value = {
            "roles": {
                "DEVELOPER": "You are a software developer.",
                "QA": "You are a QA engineer.",
                "ARCHITECT": "You are an architect.",
                "PO": "You are a product owner.",
                "DEVOPS": "You are a DevOps engineer.",
                "DATA": "You are a data engineer."
            }
        }
        mock.get_system_prompt_template.return_value = """{role_prompt}

  You have access to the following tools:
  {capabilities}

  Mode: {mode}

  Generate a step-by-step execution plan in JSON format."""
        mock.get_user_prompt_template.return_value = """Task: {task}

  Context:
  {context}

  Generate an execution plan as a JSON object with this structure:
  {{
    "reasoning": "Why this approach...",
    "steps": [
      {{"tool": "files", "operation": "read_file", "params": {{"path": "src/file.py"}}}},
      {{"tool": "tests", "operation": "pytest", "params": {{"path": "tests/"}}}},
      ...
    ]
  }}

  Use ONLY the available tools listed above. Be specific with file paths based on the context."""
        return mock

    @pytest.fixture
    def json_parser(self):
        """Create a mock JSONResponseParser."""
        from core.agents_and_tools.agents.infrastructure.services.json_response_parser import (
            JSONResponseParser,
        )
        # Use real parser for tests (parsing is simple logic)
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
        """Create a GeneratePlanUseCase instance with mocked dependencies."""
        return GeneratePlanUseCase(
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

    @pytest.mark.asyncio
    async def test_execute_success(self, usecase, llm_client, available_tools, dev_role):
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
            role=dev_role,
            available_tools=available_tools,
            constraints=None
        )

        # Assert
        assert result.reasoning == "We need to implement authentication"
        assert len(result.steps) == 2
        assert result.steps[0].tool == "files"
        assert llm_client.generate.called

    @pytest.mark.asyncio
    async def test_execute_with_markdown_wrapper(self, usecase, llm_client, available_tools, dev_role):
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
            role=dev_role,
            available_tools=available_tools
        )

        # Assert
        assert result.reasoning == "Test reasoning"
        assert len(result.steps) == 1

    @pytest.mark.asyncio
    async def test_execute_with_plain_code_block(self, usecase, llm_client, available_tools, dev_role):
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
            role=dev_role,
            available_tools=available_tools
        )

        # Assert
        assert len(result.steps) == 1

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json(self, usecase, llm_client, available_tools, dev_role):
        """Test handling of invalid JSON response."""
        llm_client.generate = AsyncMock(return_value="Invalid JSON response")

        # Execute - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to parse JSON response"):
            await usecase.execute(
                task="Test task",
                context="Test context",
                role=dev_role,
                available_tools=available_tools
            )

    @pytest.mark.asyncio
    async def test_execute_with_missing_steps(self, usecase, llm_client, available_tools, dev_role):
        """Test handling of response missing 'steps' field."""
        llm_client.generate = AsyncMock(return_value=json.dumps({"reasoning": "Test"}))

        # Execute - should raise ValueError
        with pytest.raises(ValueError, match="Plan missing 'steps' field"):
            await usecase.execute(
                task="Test task",
                context="Test context",
                role=dev_role,
                available_tools=available_tools
            )

    @pytest.mark.asyncio
    async def test_execute_with_custom_role(self, usecase, llm_client, available_tools, qa_role):
        """Test plan generation for QA role."""
        response_data = {
            "reasoning": "Need to create tests",
            "steps": [{"tool": "tests", "operation": "pytest", "params": {"path": "tests/"}}]
        }
        llm_client.generate = AsyncMock(return_value=json.dumps(response_data))

        # Execute
        await usecase.execute(
            task="Create test coverage",
            context="Project has auth module",
            role=qa_role,
            available_tools=available_tools
        )

        # Assert
        assert llm_client.generate.called
        call_args = llm_client.generate.call_args
        # System prompt should contain QA role
        assert "QA" in call_args[0][0] or "testing" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_execute_with_constraints(self, usecase, llm_client, available_tools, dev_role):
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
            role=dev_role,
            available_tools=available_tools,
            constraints=constraints
        )

        # Assert
        assert len(result.steps) == 1

