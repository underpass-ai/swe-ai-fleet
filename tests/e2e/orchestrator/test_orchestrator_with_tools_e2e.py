"""
E2E test for Orchestrator → Ray → VLLMAgent → Tools flow.

This test validates the complete flow:
1. Orchestrator receives task via gRPC
2. Gets smart context from Context Service
3. Submits Ray job with workspace
4. VLLMAgent executes task using tools
5. Results published to NATS
6. Context Service updated with changes

This demonstrates the key innovation: Smart context + focused tools.
"""

import asyncio
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with a simple Python project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)

        # Create project structure
        (workspace / "src").mkdir()
        (workspace / "tests").mkdir()
        (workspace / "src" / "__init__.py").write_text("")
        (workspace / "src" / "utils.py").write_text(
            "# Utility functions\n\n"
            "def existing_function():\n"
            "    return 'exists'\n"
        )
        (workspace / "tests" / "test_utils.py").write_text(
            "from src.utils import existing_function\n\n"
            "def test_existing():\n"
            "    assert existing_function() == 'exists'\n"
        )

        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=workspace, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test Agent"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@agent.local"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )

        yield workspace


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_vllm_agent_with_smart_context(temp_workspace):
    """
    Test VLLMAgent executes task with smart context from Context Service.

    This simulates the full flow:
    1. Context Service provides smart, filtered context (2-4K tokens)
    2. Agent receives task + context
    3. Agent uses tools to complete task
    4. Agent returns results with operations and artifacts
    """
    from pathlib import Path

    from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
        AgentInitializationConfig,
    )
    from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import (
        VLLMAgentFactory,
    )

    # Simulate smart context from Context Service
    smart_context = """
Story: US-123 - Improve utility functions
Phase: BUILD
Role: DEV

Relevant Decisions:
- Decision-001: Use Python 3.13 type hints (ARCHITECT)
- Decision-002: Maintain >90% test coverage (QA)

Existing Code:
- src/utils.py exists with existing_function()
- tests/test_utils.py has basic tests

Task Requirements:
- Add new function to utils.py
- Ensure tests still pass
- Use type hints
"""

    # Create agent config following DDD/Hexagonal architecture
    import os

    from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory

    config = AgentInitializationConfig(
        agent_id="agent-dev-001",
        role=RoleFactory.create_developer(),  # RBAC Role object
        workspace_path=Path(temp_workspace),
        vllm_url=os.getenv(
            "VLLM_URL",
            "http://vllm-server.swe-ai-fleet.svc.cluster.local:8000",
        ),
        enable_tools=True,  # Full execution mode
    )

    # Use factory to create agent with all dependencies injected
    agent = VLLMAgentFactory.create(config)

    # Execute task with smart context
    from core.agents_and_tools.agents.domain.entities.core.execution_constraints import (
        ExecutionConstraints,
    )

    constraints = ExecutionConstraints(
        max_operations=20,
        abort_on_error=False,  # Continue even if pytest fails
        iterative=False,
    )

    result = await agent.execute_task(
        task="Add a hello_world() function to src/utils.py that returns 'Hello, World!'",
        context=smart_context,  # Smart, filtered context
        constraints=constraints,
    )

    # Verify execution (main goal: function added)
    # Note: Overall success may be False if pytest fails, but file ops should succeed
    all_operations = result.operations.get_all()
    assert len(all_operations) > 0, "No operations executed"
    assert len(all_operations) < 10, "Too many operations (should be focused)"

    # Verify function was added
    utils_content = (temp_workspace / "src" / "utils.py").read_text()
    assert "hello_world" in utils_content
    assert "def hello_world()" in utils_content

    # Verify artifacts (may be files_modified or files_changed)
    # Artifacts is a collection entity, check if it has file-related artifacts
    all_artifacts = result.artifacts.get_all()
    artifact_names = [a.name for a in all_artifacts]
    has_file_artifact = any(
        name in ("files_modified", "files_changed", "files_read")
        for name in artifact_names
    )
    assert has_file_artifact, f"Missing file artifact. Got: {artifact_names}"

    # Verify focused tool usage (key innovation!)
    # Operations is a collection entity with Operation entities
    file_ops = result.operations.get_by_tool("files")
    assert len(file_ops) <= 5, "Should read/write specific files, not scan repo"

    # Verify file operations succeeded
    successful_file_ops = [op for op in file_ops if op.success]
    assert len(successful_file_ops) > 0, "At least some file operations should succeed"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_vllm_agent_read_only_planning(temp_workspace):
    """
    Test agent in read-only mode (planning/analysis).

    Agent can use tools to analyze but not modify code.
    This is useful for:
    - ARCHITECT agents doing analysis
    - Planning phase before execution
    - Code review and proposals
    """
    from pathlib import Path

    from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
        AgentInitializationConfig,
    )
    from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import (
        VLLMAgentFactory,
    )

    # Simulate planning context
    context = """
Story: US-124 - Refactor authentication
Phase: DESIGN
Role: ARCHITECT

Task: Analyze current auth implementation
"""

    # Create agent config in read-only mode
    import os

    from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory

    config = AgentInitializationConfig(
        agent_id="agent-architect-001",
        role=RoleFactory.create_architect(),  # RBAC Role object
        workspace_path=Path(temp_workspace),
        vllm_url=os.getenv(
            "VLLM_URL",
            "http://vllm-server.swe-ai-fleet.svc.cluster.local:8000",
        ),
        enable_tools=False,  # Read-only mode
    )

    # Use factory to create agent with all dependencies injected
    agent = VLLMAgentFactory.create(config)

    # Get available tools (returns AgentCapabilities entity)
    tools_info = agent.get_available_tools()
    assert tools_info.mode == "read_only"
    # Capabilities include signatures; check by prefix
    assert any(cap.startswith("files.read_file") for cap in tools_info.capabilities)
    assert not any(cap.startswith("files.write_file") for cap in tools_info.capabilities)

    # Execute analysis task
    from core.agents_and_tools.agents.domain.entities.core.execution_constraints import (
        ExecutionConstraints,
    )
    result = await agent.execute_task(
        task="Analyze the structure of utils.py",
        context=context,
        constraints=ExecutionConstraints(),
    )

    # Verify operations are read-only
    # Operations is a collection entity with Operation entities
    all_operations = result.operations.get_all()
    for op in all_operations:
        tool_name = op.tool_name
        operation = op.operation
        # Should only be read operations
        assert operation in [
            "read_file",
            "list_files",
            "search_in_files",
            "status",
            "log",
        ], f"Write operation {operation} should be blocked"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_ray_vllm_agent_job_with_tools():
    """
    Test Ray VLLMAgentJob executes agent with tools.

    This requires:
    - Ray cluster running
    - NATS server running
    - Workspace available

    Flow:
    1. Create Ray actor with tools enabled
    2. Submit job
    3. Agent executes task
    4. Results published to NATS
    """
    pytest.skip("VLLMAgentJob module needs to be implemented - test placeholder")

    # Connect to Ray
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    # Create workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "src").mkdir()
        (workspace / "src" / "utils.py").write_text("# Utils\n")

        # Create Ray actor with tools
        agent_actor = VLLMAgentJob.remote(
            agent_id="agent-dev-ray-001",
            role="DEV",
            vllm_url="http://localhost:8000",  # Assuming local vLLM
            model="Qwen/Qwen3-0.6B",
            nats_url="nats://localhost:4222",
            workspace_path=str(workspace),
            enable_tools=True,  # ENABLE TOOLS
        )

        # Submit job
        job_ref = agent_actor.run.remote(
            task_id="test-task-001",
            task_description="Add hello() function to src/utils.py",
            constraints={"context": "Python project"},
            diversity=False,
        )

        # Wait for result (with timeout)
        result = ray.get(job_ref, timeout=60)

        # Verify result
        assert result["task_id"] == "test-task-001"
        assert "operations" in result, "Should have operations (tool-enabled)"
        assert "artifacts" in result, "Should have artifacts"

        # Verify function was added
        utils_content = (workspace / "src" / "utils.py").read_text()
        assert "hello" in utils_content


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_orchestrator_to_tools_flow():
    """
    Test complete flow: Orchestrator → Context → Ray → VLLMAgent → Tools.

    This is the ULTIMATE E2E test demonstrating:
    1. Orchestrator receives gRPC request
    2. Calls Context Service for smart context
    3. Submits Ray job with workspace
    4. Agent executes using tools
    5. Results published to NATS
    6. Context Service updated

    Requires:
    - All services deployed (Orchestrator, Context, NATS, Neo4j, Ray, vLLM)
    - Test workspace available
    - Network connectivity
    """
    pytest.skip("OrchestrateFullRequest API not implemented yet - test placeholder")

    import grpc
    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc

    # Connect to Orchestrator
    channel = grpc.aio.insecure_channel("localhost:50055")
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

    # Call OrchestrateFull with tools enabled
    request = orchestrator_pb2.OrchestrateFullRequest(
        task_id="e2e-test-001",
        story_id="US-999",
        role="DEV",
        task_description="Add greeting() function to utils.py",
        enable_tools=True,  # KEY: Enable tool execution
        workspace_config={
            "repo_url": "https://github.com/underpass-ai/swe-ai-fleet.git",
            "branch": "feature/agent-tools-enhancement",
        },
    )

    # Execute (async deliberation)
    response = await stub.OrchestrateWithTools(request)

    # Verify response
    assert response.task_id == "e2e-test-001"
    assert response.status == "submitted"
    assert response.enable_tools is True

    # Wait for results (would normally come via NATS)
    # For E2E, we can poll GetDeliberationResult
    await asyncio.sleep(30)  # Give agents time to execute

    # Get results
    result_req = orchestrator_pb2.GetDeliberationResultRequest(task_id="e2e-test-001")
    result_resp = await stub.GetDeliberationResult(result_req)

    # Verify tool execution results
    assert result_resp.status == "completed"
    assert len(result_resp.winner.operations) > 0, "Should have executed tools"
    assert len(result_resp.winner.artifacts) > 0, "Should have artifacts"

    # Verify artifacts
    artifacts = result_resp.winner.artifacts
    assert "commit_sha" in artifacts or "files_modified" in artifacts

    await channel.close()

