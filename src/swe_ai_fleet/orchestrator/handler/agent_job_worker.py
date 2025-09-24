# src/swe_ai_fleet/orchestrator/agent_job_native.py
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import ray
from swe_ai_fleet.context.usecases.rehydrate_context import RehydrateContextUseCase

from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort
from swe_ai_fleet.context.ports.graph_query_port import GraphQueryPort
from swe_ai_fleet.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase
from swe_ai_fleet.orchestrator.config_module.agent_configuration import AgentConfig
from swe_ai_fleet.orchestrator.domain import TaskExecutionResult, TaskSelectionService, TaskStatus
from swe_ai_fleet.orchestrator.dto import AgentJobEventDTO, ExecutionResponseDTO


@ray.remote(num_cpus=1)
class AgentJobWorker:
    """
    Orchestrates the agent loop: rehydrate -> pick task -> run in runner -> update context.
    """
    def __init__(
        self,
        config: AgentConfig,
        graph_query: GraphQueryPort,
        graph_command: GraphCommandPort,
        planning_read: Any | None = None,
    ) -> None:
        self.cfg = config
        self.gq = graph_query
        self.gc = graph_command
        self.pr = planning_read

    def run_once(self) -> dict:
        ctx = RehydrateContextUseCase(self.gq, self.pr).execute(
            sprint_id=self.cfg.sprint_id, role=self.cfg.role
        )

        # Use domain service for task selection
        task = TaskSelectionService.select_task(ctx.tasks, pick_first=self.cfg.pick_first_ready)
        if not task:
            noop_response = ExecutionResponseDTO.noop("no candidate tasks")
            return noop_response.to_dict()

        UpdateSubtaskStatusUseCase(self.gc).execute(task_id=task.id, new_status=TaskStatus.IN_PROGRESS.value)

        # Mock execution result since runner is removed
        mock_result = {
            "exit_code": 0,
            "artifacts_dir": f"/workspace/artifacts/{task.id}",
        }
        
        # Use domain entity for execution result
        execution_result = TaskExecutionResult.from_runner_result(task.id, mock_result)
        UpdateSubtaskStatusUseCase(self.gc).execute(task_id=task.id, new_status=execution_result.status.value)

        self._append_event(
            task_id=task.id,
            status=execution_result.status.value,
            artifacts=execution_result.artifacts_dir,
        )
        
        # Return appropriate response based on execution result
        if execution_result.is_successful:
            success_response = ExecutionResponseDTO.success(task.id, execution_result.artifacts_dir)
            return success_response.to_dict()
        else:
            failed_response = ExecutionResponseDTO.failed(
                task.id, f"Task execution failed with exit code {execution_result.exit_code}"
            )
            return failed_response.to_dict()

    # --- helpers ---


    def _append_event(self, task_id: str, status: str, artifacts: str) -> None:
        event_dto = AgentJobEventDTO(
            timestamp=datetime.utcnow().isoformat(),
            sprint_id=self.cfg.sprint_id,
            task_id=task_id,
            role=self.cfg.role,
            status=status,
            artifacts=artifacts,
            component="AgentWorker",
        )
        print(json.dumps(event_dto.to_dict(), ensure_ascii=False))
