# src/swe_ai_fleet/orchestrator/agent_job_native.py
from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Any, List

import ray

# Import ports/usecases from your repo. Adjust names if they differ.
# The point is: do not duplicate DTOs; use the existing ones.
try:
    from swe_ai_fleet.context.ports.graph_query_port import GraphQueryPort
    from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort
    # Optional planning read (Redis)
    try:
        from swe_ai_fleet.context.ports.planning_read_port import PlanningReadPort
    except Exception:
        PlanningReadPort = None  # type: ignore

    # Usecases names may differ; wire your actual ones here.
    # Provide thin wrappers if needed.
    from swe_ai_fleet.context.usecases.rehydrate_context import RehydrateContextUseCase  # noqa
    from swe_ai_fleet.context.usecases.update_subtask_status import UpdateSubtaskStatusUseCase  # noqa
except Exception as e:  # pragma: no cover
    raise ImportError(
        f"Adjust imports to existing ports/usecases. Import error: {e}"
    )


class RunnerPort(Protocol):
    def run(self, spec: dict, workspace: str) -> dict: ...


@dataclass(frozen=True)
class AgentConfig:
    sprint_id: str
    role: str
    workspace: str = "/workspace"
    pick_first_ready: bool = True  # naive heuristic for MVP


@ray.remote(num_cpus=1)
class AgentWorker:
    """
    Orchestrates the agent loop: rehydrate -> pick task -> run in runner -> update context.
    """
    def __init__(
        self,
        config: AgentConfig,
        graph_query: GraphQueryPort,
        graph_command: GraphCommandPort,
        runner: RunnerPort,
        planning_read: Optional[Any] = None,
    ) -> None:
        self.cfg = config
        self.gq = graph_query
        self.gc = graph_command
        self.runner = runner
        self.pr = planning_read

    def run_once(self) -> dict:
        ctx = RehydrateContextUseCase(self.gq, self.pr).execute(
            sprint_id=self.cfg.sprint_id, role=self.cfg.role
        )

        # Expect ctx.tasks items with .status/.id/.title according to your domain DTOs
        candidates = [t for t in ctx.tasks if str(t.status) in ("READY", "IN_PROGRESS")]
        if not candidates:
            return {"status": "NOOP", "reason": "no candidate tasks"}

        task = candidates[0] if self.cfg.pick_first_ready else self._pick_by_priority(candidates)

        UpdateSubtaskStatusUseCase(self.gc).execute(task_id=task.id, new_status="IN_PROGRESS")

        spec = self._build_spec(task)
        result = self.runner.run(spec, self.cfg.workspace)

        final_status = "DONE" if (result.get("exit_code", 1) == 0) else "FAILED"
        UpdateSubtaskStatusUseCase(self.gc).execute(task_id=task.id, new_status=final_status)

        self._append_event(task_id=task.id, status=final_status, artifacts=result.get("artifacts_dir", self.cfg.workspace))
        return {"status": final_status, "task_id": task.id, "artifacts": result.get("artifacts_dir")}

    # --- helpers ---

    def _build_spec(self, task) -> dict:
        # Keep it simple and policy-safe for the MVP.
        return {
            "tool": "echo",
            "args": [f"Working on {getattr(task, 'title', task.id)}"],
            "env": {},
            "timeout_sec": 60,
        }

    def _pick_by_priority(self, tasks: List[Any]):
        # Extend with domain's priority criteria if available
        return tasks[0]

    def _append_event(self, task_id: str, status: str, artifacts: str) -> None:
        payload = {
            "ts": datetime.utcnow().isoformat(),
            "sprint_id": self.cfg.sprint_id,
            "task_id": task_id,
            "role": self.cfg.role,
            "status": status,
            "artifacts": artifacts,
            "component": "AgentWorker",
        }
        print(json.dumps(payload, ensure_ascii=False))
