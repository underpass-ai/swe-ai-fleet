"""Unit tests for VLLMAgent RBAC enforcement.

Tests verify that RBAC is enforced at runtime, preventing privilege escalation
through LLM manipulation or malicious inputs.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from core.agents_and_tools.agents.application.services.step_execution_service import (
    StepExecutionApplicationService,
)
from core.agents_and_tools.agents.domain.entities import ExecutionStep
from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)
from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import VLLMAgentFactory


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def create_test_config(workspace_path, role="developer", **kwargs):
    """Helper to create AgentInitializationConfig for tests."""
    role_obj = RoleFactory.create_role_by_name(role)
    return AgentInitializationConfig(
        agent_id="test-rbac-agent",
        role=role_obj,
        workspace_path=workspace_path,
        vllm_url="http://vllm:8000",
        **kwargs
    )


# =============================================================================
# VLLMAgent RBAC Enforcement Tests
# =============================================================================

class TestVLLMAgentRBACEnforcement:
    """Test RBAC enforcement in VLLMAgent._execute_step()."""

    @pytest.mark.asyncio
    async def test_architect_cannot_execute_docker_tool(self, temp_workspace):
        """Architect agent should fail when trying to execute docker operations."""
        # Arrange: Create architect agent (allowed: files, git, db, http)
        config = create_test_config(temp_workspace, role="architect")
        agent = VLLMAgentFactory.create(config)

        # Verify architect doesn't have docker access
        assert not agent.can_use_tool("docker")
        assert agent.can_use_tool("files")

        # Create step using DISALLOWED tool
        disallowed_step = ExecutionStep(
            tool="docker",
            operation="build",
            params={"dockerfile": "Dockerfile"}
        )

        # Act: Try to execute step with disallowed tool
        result = await agent._execute_step(disallowed_step)

        # Assert: Should fail with RBAC violation
        assert result.success is False
        assert "RBAC Violation" in result.error
        assert "docker" in result.error.lower()
        assert "architect" in result.error.lower()

    @pytest.mark.asyncio
    async def test_qa_cannot_execute_git_commit(self, temp_workspace):
        """QA agent should fail when trying to commit code."""
        # Arrange: Create QA agent (allowed: files, tests, http)
        config = create_test_config(temp_workspace, role="qa")
        agent = VLLMAgentFactory.create(config)

        # Verify QA doesn't have git access
        assert not agent.can_use_tool("git")
        assert agent.can_use_tool("files")
        assert agent.can_use_tool("tests")

        # Create step using DISALLOWED tool
        disallowed_step = ExecutionStep(
            tool="git",
            operation="commit",
            params={"message": "malicious commit"}
        )

        # Act: Try to execute step with disallowed tool
        result = await agent._execute_step(disallowed_step)

        # Assert: Should fail with RBAC violation
        assert result.success is False
        assert "RBAC Violation" in result.error
        assert "git" in result.error.lower()

    # NOTE: PO role test skipped - profile not created yet
    # Will be added when core/agents_and_tools/resources/profiles/po.yaml is created

    @pytest.mark.asyncio
    async def test_developer_CAN_execute_allowed_tools(self, temp_workspace):
        """Developer agent should successfully execute allowed tools."""
        # Arrange: Create developer agent (allowed: files, git, tests)
        config = create_test_config(temp_workspace, role="developer")
        agent = VLLMAgentFactory.create(config)

        # Verify developer HAS access to these tools
        assert agent.can_use_tool("files")
        assert agent.can_use_tool("git")
        assert agent.can_use_tool("tests")

        # Create step using ALLOWED tool
        allowed_step = ExecutionStep(
            tool="files",
            operation="list_files",
            params={"path": str(temp_workspace)}
        )

        # Act: Execute step with allowed tool
        result = await agent._execute_step(allowed_step)

        # Assert: Should succeed (or fail for other reasons, but NOT RBAC)
        # The error should NOT mention RBAC
        if not result.success:
            assert "RBAC Violation" not in result.error

    @pytest.mark.asyncio
    async def test_devops_cannot_execute_database_operations(self, temp_workspace):
        """DevOps agent should fail when trying to execute database operations."""
        # Arrange: Create devops agent (allowed: docker, files, http, tests)
        config = create_test_config(temp_workspace, role="devops")
        agent = VLLMAgentFactory.create(config)

        # Verify devops doesn't have db access
        assert not agent.can_use_tool("db")
        assert agent.can_use_tool("docker")

        # Create step using DISALLOWED tool
        disallowed_step = ExecutionStep(
            tool="db",
            operation="migrate",
            params={}
        )

        # Act: Try to execute step with disallowed tool
        result = await agent._execute_step(disallowed_step)

        # Assert: Should fail with RBAC violation
        assert result.success is False
        assert "RBAC Violation" in result.error
        assert "db" in result.error.lower()


# =============================================================================
# StepExecutionApplicationService RBAC Enforcement Tests
# =============================================================================

class TestStepExecutionServiceRBACEnforcement:
    """Test RBAC enforcement in StepExecutionApplicationService."""

    @pytest.mark.asyncio
    async def test_rejects_disallowed_tool(self):
        """Should reject execution of disallowed tools."""
        # Arrange
        mock_port = Mock()
        allowed_tools = frozenset({"files", "git"})  # Only files and git
        service = StepExecutionApplicationService(
            tool_execution_port=mock_port,
            allowed_tools=allowed_tools,
        )

        # Create step with DISALLOWED tool
        step = ExecutionStep(tool="docker", operation="build", params={})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is False
        assert "RBAC Violation" in result.error
        assert "docker" in result.error.lower()
        assert "['files', 'git']" in result.error  # Shows allowed tools

        # Verify port was NEVER called (security)
        mock_port.execute_operation.assert_not_called()

    @pytest.mark.asyncio
    async def test_allows_execution_of_allowed_tools(self):
        """Should execute allowed tools successfully."""
        # Arrange
        mock_port = Mock()
        result_mock = Mock()
        result_mock.success = True
        result_mock.error = None
        mock_port.execute_operation.return_value = result_mock

        allowed_tools = frozenset({"files", "git", "tests"})
        service = StepExecutionApplicationService(
            tool_execution_port=mock_port,
            allowed_tools=allowed_tools,
        )

        # Create step with ALLOWED tool
        step = ExecutionStep(tool="files", operation="read_file", params={"path": "test.py"})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert
        assert result.success is True

        # Verify port WAS called (authorized)
        mock_port.execute_operation.assert_called_once()

    @pytest.mark.asyncio
    async def test_rbac_violation_returns_error(self):
        """Should return error DTO when RBAC is violated."""
        # Arrange
        mock_port = Mock()
        allowed_tools = frozenset({"files"})
        service = StepExecutionApplicationService(
            tool_execution_port=mock_port,
            allowed_tools=allowed_tools,
        )

        # Create step with DISALLOWED tool
        step = ExecutionStep(tool="docker", operation="build", params={})

        # Act
        result = await service.execute(step, enable_write=True)

        # Assert: Should return error DTO with RBAC violation message
        assert result.success is False
        assert "RBAC Violation" in result.error
        assert "docker" in result.error.lower()
        assert "['files']" in result.error  # Shows allowed tools for debugging


# =============================================================================
# Cross-Role RBAC Tests
# =============================================================================

class TestCrossRoleRBACEnforcement:
    """Test RBAC enforcement across different roles."""

    @pytest.mark.asyncio
    async def test_all_roles_enforce_tool_restrictions(self, temp_workspace):
        """All roles should enforce their respective tool restrictions."""
        test_cases = [
            # RBAC restrictions (should DENY)
            ("architect", "docker", False),    # Architect cannot use docker
            ("qa", "git", False),              # QA cannot use git
            ("developer", "db", False),        # Developer cannot use db
            ("devops", "db", False),           # DevOps cannot use db
            ("data", "docker", False),         # Data cannot use docker

            # RBAC permissions (should ALLOW)
            ("architect", "files", True),      # Architect CAN use files
            ("qa", "tests", True),             # QA CAN use tests
            ("developer", "git", True),        # Developer CAN use git
            ("devops", "docker", True),        # DevOps CAN use docker
            ("data", "db", True),              # Data CAN use db
        ]

        for role, tool, should_allow in test_cases:
            # Create agent with specific role
            config = create_test_config(temp_workspace, role=role)
            agent = VLLMAgentFactory.create(config)

            # Verify permission
            can_use = agent.can_use_tool(tool)

            assert can_use == should_allow, (
                f"Role '{role}' tool '{tool}' permission mismatch: "
                f"expected {should_allow}, got {can_use}"
            )

