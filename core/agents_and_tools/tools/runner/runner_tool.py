#!/usr/bin/env python3
"""
SWE AI Fleet Runner Tool - MCP Implementation

This module implements the Runner Tool that provides the TaskSpec/TaskResult contract
for agent-container interactions. It supports both local (Docker) and
Kubernetes execution modes.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TaskSpec:
    """Task specification for container execution"""

    image: str
    cmd: list[str]
    env: dict[str, str]
    mounts: list[dict[str, str]]
    timeouts: dict[str, int]
    resources: dict[str, str]
    artifacts: dict[str, list[str]]
    context: dict[str, Any] | None = None


@dataclass
class TaskResult:
    """Task execution result"""

    status: TaskStatus
    exitCode: int
    captured: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class TaskInfo:
    """Internal task tracking information"""

    task_id: str
    spec: TaskSpec
    status: TaskStatus
    container_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    logs: list[str] | None = None
    artifacts: dict[str, str] | None = None


class RunnerTool:
    """
    MCP Runner Tool implementation

    Provides methods for running tasks in containers with TaskSpec/TaskResult contract.
    Supports both local (Podman/Docker) and Kubernetes execution modes.
    """

    def __init__(self, runtime: str = "auto", registry: str = "localhost"):
        """
        Initialize Runner Tool

        Args:
            runtime: Container runtime ("docker", "kubernetes", "auto")
            registry: Container registry for image references
        """
        self.runtime = self._detect_runtime(runtime)
        self.registry = registry
        self.tasks: dict[str, TaskInfo] = {}
        self.logger = logging.getLogger(f"{__name__}.RunnerTool")

    def _detect_runtime(self, runtime: str) -> str:
        """Detect available container runtime"""
        if runtime != "auto":
            return runtime

        # Check for Kubernetes
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            return "kubernetes"

        # Check for Docker
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            return "docker"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback: default to docker label for non-executing operations in tests
        # Methods like stream_logs/await_result/cancel do not require a runtime.
        return "docker"

    async def run_task(self, spec: TaskSpec) -> str:
        """
        Start a task execution

        Args:
            spec: Task specification

        Returns:
            task_id: Unique identifier for the task
        """
        task_id = str(uuid.uuid4())

        # Create task info
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PENDING, logs=[], artifacts={})

        self.tasks[task_id] = task_info

        # Start execution based on runtime
        if self.runtime == "kubernetes":
            await self._run_kubernetes_task(task_info)
        else:
            await self._run_local_task(task_info)

        return task_id

    async def _run_local_task(self, task_info: TaskInfo):
        """Run task using local container runtime (Docker)"""
        try:
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.now(UTC)

            # Build docker command
            cmd = [self.runtime, "run", "--rm"]

            # Add mounts
            for mount in task_info.spec.mounts:
                if mount["type"] == "bind":
                    cmd.extend(["-v", f"{mount['source']}:{mount['target']}:Z"])

            # Add environment variables
            for key, value in task_info.spec.env.items():
                cmd.extend(["-e", f"{key}={value}"])

            # Add image and command
            cmd.append(task_info.spec.image)
            cmd.extend(task_info.spec.cmd)

            self.logger.info(f"Running local task {task_info.task_id}: {' '.join(cmd)}")

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )

            # Stream logs
            async for line in process.stdout:
                line_str = line.decode().strip()
                task_info.logs.append(line_str)
                self.logger.debug(f"Task {task_info.task_id}: {line_str}")

            # Wait for completion
            exit_code = await process.wait()
            task_info.finished_at = datetime.now(UTC)

            # Determine status
            if exit_code == 0:
                task_info.status = TaskStatus.PASSED
            else:
                task_info.status = TaskStatus.FAILED

        except Exception as e:
            self.logger.error(f"Task {task_info.task_id} failed: {e}")
            task_info.status = TaskStatus.ERROR
            task_info.finished_at = datetime.now(UTC)

    async def _run_kubernetes_task(self, task_info: TaskInfo):
        """Run task using Kubernetes Jobs API"""
        # This would implement Kubernetes Job creation and monitoring
        # For now, raise NotImplementedError
        raise NotImplementedError("Kubernetes execution not yet implemented")

    async def stream_logs(self, task_id: str) -> list[str]:
        """
        Stream logs for a running task

        Args:
            task_id: Task identifier

        Returns:
            List of log lines
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task_info = self.tasks[task_id]
        return task_info.logs.copy()

    async def await_result(self, task_id: str, timeout_sec: int | None = None) -> TaskResult:
        """
        Wait for task completion and return result

        Args:
            task_id: Task identifier
            timeout_sec: Maximum wait time in seconds

        Returns:
            TaskResult with execution details
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task_info = self.tasks[task_id]

        # Wait for completion
        start_time = time.time()
        while task_info.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            if timeout_sec and (time.time() - start_time) > timeout_sec:
                task_info.status = TaskStatus.TIMEOUT
                break
            await asyncio.sleep(0.1)

        # Build result
        duration = None
        if task_info.started_at and task_info.finished_at:
            duration = int((task_info.finished_at - task_info.started_at).total_seconds())

        result = TaskResult(
            status=task_info.status,
            exitCode=0 if task_info.status == TaskStatus.PASSED else 1,
            captured={
                "logsRef": f"s3://fleet-builds/{task_id}/logs.ndjson",  # Placeholder
                "artifacts": [
                    {"path": path, "ref": f"s3://fleet-builds/{task_id}/{path.split('/')[-1]}/"}
                    for path in task_info.spec.artifacts["paths"]
                ],
            },
            metadata={
                "containerId": task_info.container_id or "unknown",
                "imageDigest": "sha256:...",  # Placeholder
                "startedAt": task_info.started_at.isoformat() + "Z" if task_info.started_at else None,
                "finishedAt": task_info.finished_at.isoformat() + "Z" if task_info.finished_at else None,
                "duration": duration,
                "case_id": task_info.spec.context.get("case_id") if task_info.spec.context else None,
                "task_id": task_info.spec.context.get("task_id") if task_info.spec.context else None,
            },
        )

        return result

    async def copy_artifacts(self, task_id: str, path: str) -> str:
        """
        Copy artifacts from task execution

        Args:
            task_id: Task identifier
            path: Artifact path

        Returns:
            Reference to copied artifact
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        # Placeholder implementation
        return f"s3://fleet-builds/{task_id}/{path.split('/')[-1]}/"

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task_info = self.tasks[task_id]

        if task_info.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task_info.status = TaskStatus.ERROR
            task_info.finished_at = datetime.now(UTC)
            return True

        return False

    async def health(self) -> dict[str, Any]:
        """
        Check runner tool health

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "runtime": self.runtime,
            "registry": self.registry,
            "active_tasks": len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING]),
            "total_tasks": len(self.tasks),
        }


# MCP Tool interface functions
async def run_task(spec_dict: dict[str, Any]) -> str:
    """MCP tool function: run_task"""
    spec = TaskSpec(**spec_dict)
    runner = RunnerTool()
    return await runner.run_task(spec)


async def stream_logs(task_id: str) -> list[str]:
    """MCP tool function: stream_logs"""
    runner = RunnerTool()
    return await runner.stream_logs(task_id)


async def await_result(task_id: str, timeout_sec: int | None = None) -> dict[str, Any]:
    """MCP tool function: await_result"""
    runner = RunnerTool()
    result = await runner.await_result(task_id, timeout_sec)
    return asdict(result)


async def copy_artifacts(task_id: str, path: str) -> str:
    """MCP tool function: copy_artifacts"""
    runner = RunnerTool()
    return await runner.copy_artifacts(task_id, path)


async def cancel(task_id: str) -> bool:
    """MCP tool function: cancel"""
    runner = RunnerTool()
    return await runner.cancel(task_id)


async def health() -> dict[str, Any]:
    """MCP tool function: health"""
    runner = RunnerTool()
    return await runner.health()


if __name__ == "__main__":
    # Example usage
    async def main():
        # Example TaskSpec
        spec = TaskSpec(
            image="localhost/swe-ai-fleet-runner:latest",
            cmd=["/bin/bash", "-lc", "agent-task"],
            env={"TASK": "unit", "LANG": "python", "TEST_CMD": "echo 'Hello from container!'"},
            mounts=[
                {
                    "type": "bind",
                    "source": str(tempfile.mkdtemp(prefix="swe-runner-")),
                    "target": "/workspace",
                }
            ],
            timeouts={"overallSec": 300},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": ["/workspace/test-reports"]},
        )

        # Run task
        task_id = await run_task(asdict(spec))
        print(f"Started task: {task_id}")

        # Stream logs
        logs = await stream_logs(task_id)
        for log in logs:
            print(f"LOG: {log}")

        # Wait for result
        result = await await_result(task_id)
        print(f"Result: {result}")

    asyncio.run(main())
