"""Use case for executing tasks with tools."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.domain.entities.agent_result import AgentResult
from core.agents_and_tools.agents.domain.entities.execution_plan import ExecutionPlan
from core.agents_and_tools.agents.domain.ports.llm_client import LLMClientPort
from core.agents_and_tools.agents.domain.ports.tool_execution_port import ToolExecutionPort

logger = logging.getLogger(__name__)


class ExecuteTaskUseCase:
    """
    Use case for executing tasks with tools (static planning).
    
    This use case orchestrates:
    1. Plan generation
    2. Plan execution
    3. Result collection
    """

    def __init__(
        self,
        tool_execution_port: ToolExecutionPort,
        llm_client_port: LLMClientPort | None = None,
    ):
        """
        Initialize the use case.
        
        Args:
            tool_execution_port: Port for tool execution
            llm_client_port: Port for LLM communication (optional)
        """
        self.tool_execution_port = tool_execution_port
        self.llm_client_port = llm_client_port

    async def execute(
        self,
        task: str,
        context: str,
        constraints: dict[str, Any],
        enable_write: bool = True,
    ) -> AgentResult:
        """
        Execute a task with static planning.
        
        Args:
            task: Task description
            context: Project context
            constraints: Execution constraints
            enable_write: If False, only read operations allowed
            
        Returns:
            AgentResult with execution results
        """
        operations = []
        artifacts = {}
        audit_trail = []
        reasoning_log = []

        try:
            logger.info(f"Executing task (static): {task}")

            # Step 1: Generate execution plan
            # TODO: Call plan generation use case
            plan = ExecutionPlan(steps=[], reasoning="")
            logger.info(f"Generated plan with {len(plan.steps)} steps")

            # Step 2: Execute plan
            for i, step in enumerate(plan.steps):
                logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step}")

                result = await self._execute_step(step, enable_write)

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
                    new_artifacts = self._collect_artifacts(step, result)
                    artifacts.update(new_artifacts)

                # Check if step failed
                if not result.get("success"):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Step {i+1} failed: {error_msg}")

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

            logger.info(f"Task completed: {success} ({len(operations)} operations)")

            return AgentResult(
                success=success,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
            )

        except Exception as e:
            logger.exception(f"Task execution failed: {e}")
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=audit_trail,
                reasoning_log=reasoning_log,
                error=str(e),
            )

    async def _execute_step(self, step: dict, enable_write: bool) -> dict:
        """Execute a single plan step."""
        tool_name = step["tool"]
        operation = step["operation"]
        params = step.get("params", {})

        try:
            # Delegate to tool execution port
            result = self.tool_execution_port.execute_operation(
                tool_name=tool_name,
                operation=operation,
                params=params,
                enable_write=enable_write,
            )

            error_msg = result.error if not result.success else None
            if not result.success and not error_msg:
                error_msg = "Unknown error"

            return {
                "success": result.success,
                "result": result,
                "error": error_msg,
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _collect_artifacts(self, step: dict, result: dict) -> dict:
        """Collect artifacts from step execution."""
        # Get tool instance
        tool = self.tool_execution_port.get_tool_by_name(step["tool"])
        if not tool:
            return {}

        # Delegate to tool's collect_artifacts method
        return tool.collect_artifacts(
            step["operation"],
            result.get("result"),
            step.get("params", {}),
        )

