"""
VLLMAgent: Universal agent for SWE AI Fleet that combines vLLM reasoning with optional tool execution.

ALL agents in the system are VLLMAgents, differentiated by their ROLE:
- DEV: Implements features, fixes bugs (uses: git, files, tests)
- QA: Creates tests, validates quality (uses: files, tests, http)
- ARCHITECT: Analyzes codebase, designs solutions (uses: files, git, db for analysis)
- DEVOPS: Deploys, monitors infrastructure (uses: docker, http, files)
- DATA: Manages schemas, migrations (uses: db, files, tests)

The agent can operate in two modes:
1. **With tools**: Executes real operations (file changes, commits, tests)
2. **Without tools** (text-only): Generates proposals, deliberates (future: tool-less deliberation)

This agent receives a task, uses vLLM to generate an execution plan,
then executes the plan using real tools.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from swe_ai_fleet.tools import (
    DatabaseTool,
    DockerTool,
    FileTool,
    GitTool,
    HttpTool,
    TestTool,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result of agent task execution."""

    success: bool
    operations: list[dict]  # List of tool operations executed
    artifacts: dict[str, Any] = field(default_factory=dict)  # commit_sha, files_changed, etc
    audit_trail: list[dict] = field(default_factory=list)  # Full audit log
    error: str | None = None  # Error message if failed


@dataclass
class ExecutionPlan:
    """Structured execution plan from LLM."""

    steps: list[dict]  # [{"tool": "files", "operation": "read_file", "params": {...}}]
    reasoning: str | None = None  # Why this plan


class VLLMAgent:
    """
    Universal agent for SWE AI Fleet - combines vLLM reasoning with tool execution.

    This is THE agent class used by ALL roles in the system (DEV, QA, ARCHITECT, DEVOPS, DATA).
    The ROLE determines HOW the agent uses tools, not WHETHER it can use them.

    Workflow:
    1. Receives task: "Add hello_world() function to utils.py"
    2. Calls vLLM to generate execution plan (or uses simple pattern matching for now)
    3. Parses plan into tool operations
    4. Executes tools sequentially based on role
    5. Returns results with audit trail

    Role-Specific Tool Usage:
    - DEV: git.commit(), files.write(), tests.pytest()
    - QA: files.read(), tests.pytest(), http.post()
    - ARCHITECT: files.search(), git.log(), db.query()
    - DEVOPS: docker.build(), http.get(), files.edit()
    - DATA: db.query(), files.write(), tests.pytest()

    Example:
        # DEV agent implementing a feature
        agent = VLLMAgent(
            agent_id="agent-dev-001",
            role="DEV",
            workspace_path="/workspace/project",
            vllm_url="http://vllm:8000"
        )

        result = await agent.execute_task(
            task="Add hello_world() function to src/utils.py",
            context="Project uses Python 3.13",
            constraints={"max_operations": 10}
        )

        print(f"Success: {result.success}")
        print(f"Operations: {len(result.operations)}")
        print(f"Commit: {result.artifacts.get('commit_sha')}")

        # QA agent validating the implementation
        qa_agent = VLLMAgent(
            agent_id="agent-qa-001",
            role="QA",
            workspace_path="/workspace/project",
            vllm_url="http://vllm:8000"
        )

        result = await qa_agent.execute_task(
            task="Validate hello_world() function and create tests",
            context="Function should return 'Hello, World!'",
        )
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        workspace_path: str | Path,
        vllm_url: str | None = None,
        audit_callback: Callable | None = None,
        enable_tools: bool = True,
    ):
        """
        Initialize vLLM agent.

        Args:
            agent_id: Unique agent identifier (e.g., "agent-dev-001")
            role: Agent role - determines tool usage patterns
                  Options: DEV, QA, ARCHITECT, DEVOPS, DATA, PO
            workspace_path: Path to workspace (must exist)
            vllm_url: URL to vLLM server (optional - can use pattern matching)
            audit_callback: Callback for audit logging
            enable_tools: Whether to enable tool execution (default: True)
                         False = text-only mode (deliberation without execution)
        """
        self.agent_id = agent_id
        self.role = role.upper()  # Normalize role to uppercase
        self.workspace_path = Path(workspace_path).resolve()
        self.vllm_url = vllm_url
        self.audit_callback = audit_callback
        self.enable_tools = enable_tools

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

        # Initialize tools if enabled
        self.tools = {}
        if enable_tools:
            self.tools = {
                "git": GitTool(workspace_path, audit_callback),
                "files": FileTool(workspace_path, audit_callback),
                "tests": TestTool(workspace_path, audit_callback),
                "docker": DockerTool(workspace_path, audit_callback=audit_callback),
                "http": HttpTool(audit_callback=audit_callback),
                "db": DatabaseTool(audit_callback=audit_callback),
            }

        logger.info(
            f"VLLMAgent initialized: {agent_id} ({role}) at {workspace_path} "
            f"[tools={'enabled' if enable_tools else 'disabled'}]"
        )

    async def execute_task(
        self,
        task: str,
        context: str = "",
        constraints: dict | None = None,
    ) -> AgentResult:
        """
        Execute a task using LLM + tools.

        Args:
            task: Task description (e.g., "Add hello_world() to utils.py")
            context: Additional context about the project
            constraints: Constraints (max_operations, timeout, etc)

        Returns:
            AgentResult with success, operations, artifacts, audit_trail

        Raises:
            Exception: If critical error occurs
        """
        constraints = constraints or {}
        operations = []
        artifacts = {}
        audit_trail = []

        try:
            logger.info(f"Agent {self.agent_id} executing task: {task}")

            # Step 1: Generate execution plan
            plan = await self._generate_plan(task, context, constraints)
            logger.info(f"Generated plan with {len(plan.steps)} steps")

            # Step 2: Execute plan
            for i, step in enumerate(plan.steps):
                logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step}")

                result = await self._execute_step(step)
                operations.append(
                    {
                        "step": i + 1,
                        "tool": step["tool"],
                        "operation": step["operation"],
                        "success": result.get("success", False),
                        "error": result.get("error"),
                    }
                )

                # Collect artifacts
                if result.get("success"):
                    self._collect_artifacts(step, result, artifacts)

                # Check if step failed
                if not result.get("success"):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Step {i+1} failed: {error_msg}")

                    # Decide: abort or continue?
                    if constraints.get("abort_on_error", True):
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=audit_trail,
                            error=f"Step {i+1} failed: {error_msg}",
                        )

                # Check max operations limit
                if i + 1 >= constraints.get("max_operations", 100):
                    logger.warning("Max operations limit reached")
                    break

            # Step 3: Verify completion
            success = all(op["success"] for op in operations)

            logger.info(
                f"Task completed: {success} ({len(operations)} operations)"
            )

            return AgentResult(
                success=success,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
            )

        except Exception as e:
            logger.exception(f"Agent execution failed: {e}")
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                error=str(e),
            )

    async def _generate_plan(
        self, task: str, context: str, constraints: dict
    ) -> ExecutionPlan:
        """
        Generate execution plan from task description.

        For now: Simple pattern matching
        Future: Call vLLM for intelligent planning

        Args:
            task: Task description
            context: Project context
            constraints: Execution constraints

        Returns:
            ExecutionPlan with steps to execute
        """
        # TODO: Implement vLLM-based planning
        # For now, use simple pattern matching

        task_lower = task.lower()

        # Pattern: "add function to file"
        if "add" in task_lower and "function" in task_lower:
            return self._plan_add_function(task)

        # Pattern: "fix bug in file"
        if "fix" in task_lower or "bug" in task_lower:
            return self._plan_fix_bug(task)

        # Pattern: "run tests"
        if "test" in task_lower:
            return self._plan_run_tests(task)

        # Default: simple read and report
        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "list_files",
                    "params": {"path": ".", "recursive": False},
                }
            ],
            reasoning="Default plan: list files in workspace",
        )

    def _plan_add_function(self, task: str) -> ExecutionPlan:
        """Generate plan for adding a function to a file."""
        # Extract file name from task (simple regex or parsing)
        # For demo, assume format: "Add function_name() to file.py"

        # Default to src/utils.py if not specified
        target_file = "src/utils.py"
        function_name = "hello_world"

        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "read_file",
                    "params": {"file_path": target_file},
                },
                {
                    "tool": "files",
                    "operation": "append_file",
                    "params": {
                        "file_path": target_file,
                        "content": f'\n\ndef {function_name}():\n    """Added by agent."""\n    return "Hello, World!"\n',
                    },
                },
                {
                    "tool": "tests",
                    "operation": "pytest",
                    "params": {"path": "tests/", "markers": "not e2e"},
                },
                {
                    "tool": "git",
                    "operation": "status",
                    "params": {},
                },
            ],
            reasoning=f"Add {function_name}() to {target_file}, run tests, check status",
        )

    def _plan_fix_bug(self, task: str) -> ExecutionPlan:
        """Generate plan for fixing a bug."""
        return ExecutionPlan(
            steps=[
                {
                    "tool": "files",
                    "operation": "search_in_files",
                    "params": {"pattern": "BUG|TODO|FIXME", "path": "src/"},
                },
                {"tool": "tests", "operation": "pytest", "params": {"path": "tests/"}},
            ],
            reasoning="Search for bugs and run tests",
        )

    def _plan_run_tests(self, task: str) -> ExecutionPlan:
        """Generate plan for running tests."""
        return ExecutionPlan(
            steps=[
                {
                    "tool": "tests",
                    "operation": "pytest",
                    "params": {"path": "tests/", "verbose": True},
                }
            ],
            reasoning="Run pytest suite",
        )

    async def _execute_step(self, step: dict) -> dict:
        """
        Execute a single plan step.

        Args:
            step: {"tool": "files", "operation": "read_file", "params": {...}}

        Returns:
            {"success": bool, "result": Any, "error": str | None}
        """
        tool_name = step["tool"]
        operation = step["operation"]
        params = step.get("params", {})

        try:
            # Get tool
            tool = self.tools.get(tool_name)
            if not tool:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

            # Get method
            method = getattr(tool, operation, None)
            if not method:
                return {
                    "success": False,
                    "error": f"Unknown operation: {tool_name}.{operation}",
                }

            # Execute
            result = method(**params)

            # Check if result is a tool result object (has .success attribute)
            if hasattr(result, "success"):
                return {
                    "success": result.success,
                    "result": result,
                    "error": result.error if not result.success else None,
                }

            # Otherwise assume success
            return {"success": True, "result": result, "error": None}

        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _collect_artifacts(
        self, step: dict, result: dict, artifacts: dict
    ) -> None:
        """
        Collect artifacts from step execution.

        Artifacts:
        - commit_sha: from git.commit()
        - files_changed: list of modified files
        - test_results: from tests.pytest()
        - etc.
        """
        tool_name = step["tool"]
        operation = step["operation"]
        tool_result = result.get("result")

        # Git operations
        if tool_name == "git":
            if operation == "commit" and hasattr(tool_result, "stdout"):
                # Extract commit SHA from output
                if "commit" in tool_result.stdout.lower():
                    artifacts["commit_sha"] = tool_result.stdout.split()[1][:7]

            if operation == "status" and hasattr(tool_result, "stdout"):
                # Extract changed files
                changed = [
                    line.split()[-1]
                    for line in tool_result.stdout.split("\n")
                    if line.strip() and not line.startswith("#")
                ]
                artifacts.setdefault("files_changed", []).extend(changed)

        # Test operations
        if tool_name == "tests":
            if operation == "pytest" and hasattr(tool_result, "stdout"):
                # Extract test results
                if "passed" in tool_result.stdout.lower():
                    artifacts["tests_passed"] = True
                    # Parse "5 passed in 0.3s"
                    for word in tool_result.stdout.split():
                        if word.isdigit():
                            artifacts["tests_count"] = int(word)
                            break

        # File operations
        if tool_name == "files":
            if operation in ["write_file", "append_file", "edit_file"]:
                file_path = step["params"].get("file_path")
                if file_path:
                    artifacts.setdefault("files_modified", []).append(file_path)

