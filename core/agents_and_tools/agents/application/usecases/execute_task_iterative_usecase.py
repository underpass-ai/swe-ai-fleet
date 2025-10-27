"""Use case for executing tasks iteratively (ReAct-style)."""

from __future__ import annotations

import logging
from typing import Any

from core.agents_and_tools.agents.domain.entities.agent_result import AgentResult
from core.agents_and_tools.agents.domain.ports.tool_execution_port import ToolExecutionPort

logger = logging.getLogger(__name__)


class ExecuteTaskIterativeUseCase:
    """
    Use case for executing tasks iteratively (ReAct-style).
    
    Flow:
    1. Decide next action based on history
    2. Execute action
    3. Observe result
    4. Repeat until complete or max iterations
    """

    def __init__(self, tool_execution_port: ToolExecutionPort):
        """
        Initialize the use case.
        
        Args:
            tool_execution_port: Port for tool execution
        """
        self.tool_execution_port = tool_execution_port

    async def execute(
        self,
        task: str,
        context: str,
        constraints: dict[str, Any],
        enable_write: bool = True,
    ) -> AgentResult:
        """
        Execute task iteratively.
        
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
        observation_history = []
        reasoning_log = []

        try:
            logger.info(f"Executing task (iterative): {task}")

            max_iterations = constraints.get("max_iterations", 10)
            max_operations = constraints.get("max_operations", 100)

            for iteration in range(max_iterations):
                logger.info(f"Iteration {iteration + 1}/{max_iterations}")

                # TODO: Decide next action based on history
                next_step = await self._decide_next_action(
                    task=task,
                    context=context,
                    observation_history=observation_history,
                    constraints=constraints,
                )

                # Check if done
                if next_step.get("done", False):
                    logger.info("Task complete")
                    break

                # Execute next action
                step_info = next_step.get("step")
                if not step_info:
                    logger.warning("No step decided")
                    break

                logger.info(f"Executing: {step_info}")
                result = await self._execute_step(step_info, enable_write)

                # Record operation
                operations.append(
                    {
                        "iteration": iteration + 1,
                        "tool": step_info["tool"],
                        "operation": step_info["operation"],
                        "success": result.get("success", False),
                        "error": result.get("error"),
                    }
                )

                # Observe result
                observation = {
                    "iteration": iteration + 1,
                    "action": step_info,
                    "result": result.get("result"),
                    "success": result.get("success", False),
                    "error": result.get("error"),
                }
                observation_history.append(observation)

                # Collect artifacts
                if result.get("success"):
                    new_artifacts = self._collect_artifacts(step_info, result)
                    artifacts.update(new_artifacts)
                else:
                    # On error, decide whether to continue
                    if constraints.get("abort_on_error", True):
                        return AgentResult(
                            success=False,
                            operations=operations,
                            artifacts=artifacts,
                            audit_trail=[],
                            error=f"Iteration {iteration + 1} failed: {result.get('error')}",
                        )

                # Check limits
                if len(operations) >= max_operations:
                    logger.warning("Max operations limit reached")
                    break

            # Verify completion
            success = all(op["success"] for op in operations)

            logger.info(
                f"Task completed: {success} ({len(operations)} operations, "
                f"{len(observation_history)} iterations)"
            )

            return AgentResult(
                success=success,
                operations=operations,
                artifacts=artifacts,
                audit_trail=[],
                reasoning_log=reasoning_log,
            )

        except Exception as e:
            logger.exception(f"Iterative execution failed: {e}")
            return AgentResult(
                success=False,
                operations=operations,
                artifacts=artifacts,
                audit_trail=[],
                reasoning_log=reasoning_log,
                error=str(e),
            )

    async def _execute_step(self, step: dict, enable_write: bool) -> dict:
        """Execute a single step."""
        tool_name = step["tool"]
        operation = step["operation"]
        params = step.get("params", {})

        try:
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
        except Exception as e:
            logger.exception(f"Step execution failed: {e}")
            return {"success": False, "error": str(e)}

    async def _decide_next_action(
        self,
        task: str,
        context: str,
        observation_history: list[dict],
        constraints: dict,
    ) -> dict:
        """
        Decide next action based on history.
        
        TODO: Implement using GenerateNextActionUseCase
        """
        # Placeholder
        return {"done": True, "step": None, "reasoning": "Fallback"}

    def _collect_artifacts(self, step: dict, result: dict) -> dict:
        """Collect artifacts from step."""
        tool = self.tool_execution_port.get_tool_by_name(step["tool"])
        if not tool:
            return {}
        return tool.collect_artifacts(
            step["operation"],
            result.get("result"),
            step.get("params", {}),
        )

