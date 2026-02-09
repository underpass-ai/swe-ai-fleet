#!/usr/bin/env python3
"""E2E Test: TaskDerivationPlanningService on Planning.

This test validates two things against real deployed services:

Contract path:
1. GetPlanContext
2. CreateTasks
3. ListStoryTasks
4. SaveTaskDependencies

Async derivation path (vLLM pipeline):
5. Publish planning.plan.approved (EventEnvelope)
6. Planning consumes event and publishes task.derivation.requested
7. Task Derivation service invokes Ray/vLLM and persists derived tasks in Planning
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import grpc
import nats
import valkey
from nats.js import JetStreamContext
from neo4j import GraphDatabase

sys.path.insert(0, "/app")
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc
from fleet.task_derivation.v1 import task_derivation_pb2, task_derivation_pb2_grpc


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def print_step(step: int, description: str) -> None:
    """Print step header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}OK {message}{Colors.NC}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}ERROR {message}{Colors.NC}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}WARN {message}{Colors.NC}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.YELLOW}INFO {message}{Colors.NC}")


class TaskDerivationPlanningServiceE2E:
    """E2E validation for gRPC contract and async derivation pipeline."""

    def __init__(self) -> None:
        """Initialize test configuration."""
        self.planning_service_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )
        self.valkey_host = os.getenv("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local")
        self.valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
        self.nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "underpassai")
        self.created_by = os.getenv("TEST_CREATED_BY", "e2e-task-derivation@system.local")
        self.preserve_data = os.getenv("PRESERVE_TEST_DATA", "false").lower() == "true"
        self.derivation_timeout = int(os.getenv("DERIVATION_TIMEOUT_SECONDS", "420"))
        self.derivation_poll_interval = int(os.getenv("DERIVATION_POLL_INTERVAL_SECONDS", "10"))

        suffix = str(int(time.time()))
        self.plan_id = f"PL-E2E-{suffix}"
        self.async_plan_id = f"PL-E2E-ASYNC-{suffix}"
        self.story_title = f"E2E Task Derivation Story {suffix}"
        self.async_story_title = f"E2E Async Derivation Story {suffix}"

        self.project_id: str | None = None
        self.epic_id: str | None = None
        self.story_id: str | None = None
        self.async_story_id: str | None = None
        self.task_ids: list[str] = []
        self.async_task_ids: list[str] = []
        self.async_task_types: dict[str, str] = {}

        self.grpc_channel: grpc.aio.Channel | None = None
        self.planning_stub: planning_pb2_grpc.PlanningServiceStub | None = None
        self.task_derivation_stub: (
            task_derivation_pb2_grpc.TaskDerivationPlanningServiceStub | None
        ) = None
        self.valkey_client: Any | None = None
        self.neo4j_driver: Any | None = None
        self.nats_client: nats.NATS | None = None
        self.jetstream: JetStreamContext | None = None

    async def setup(self) -> None:
        """Set up external connections."""
        print_info("Setting up connections...")

        self.grpc_channel = grpc.aio.insecure_channel(self.planning_service_url)
        await asyncio.wait_for(self.grpc_channel.channel_ready(), timeout=15.0)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.grpc_channel)
        self.task_derivation_stub = task_derivation_pb2_grpc.TaskDerivationPlanningServiceStub(
            self.grpc_channel
        )

        self.valkey_client = valkey.Valkey(
            host=self.valkey_host,
            port=self.valkey_port,
            decode_responses=True,
        )
        self.valkey_client.ping()

        self.neo4j_driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
        )
        self.neo4j_driver.verify_connectivity()

        self.nats_client = await asyncio.wait_for(nats.connect(self.nats_url), timeout=15.0)
        self.jetstream = self.nats_client.jetstream()

        print_success("Connections ready")

    async def cleanup(self) -> None:
        """Clean up resources and temporary test data."""
        print_info("Cleaning up...")

        if not self.preserve_data:
            await self._cleanup_test_data()
        else:
            print_warning("PRESERVE_TEST_DATA=true, skipping data cleanup")

        if self.grpc_channel:
            await self.grpc_channel.close()
        if self.valkey_client:
            self.valkey_client.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.nats_client:
            await self.nats_client.close()

        print_success("Cleanup completed")

    async def _cleanup_test_data(self) -> None:
        """Best-effort cleanup for created test entities."""
        if self.valkey_client:
            for task_ids, story_id, plan_id in (
                (self.task_ids, self.story_id, self.plan_id),
                (self.async_task_ids, self.async_story_id, self.async_plan_id),
            ):
                if task_ids and story_id and plan_id:
                    task_story_set_key = f"planning:tasks:story:{story_id}"
                    task_plan_set_key = f"planning:tasks:plan:{plan_id}"
                    for task_id in task_ids:
                        self.valkey_client.delete(f"planning:task:{task_id}")
                        self.valkey_client.srem("planning:tasks:all", task_id)
                        self.valkey_client.srem(task_story_set_key, task_id)
                        self.valkey_client.srem(task_plan_set_key, task_id)

                if story_id:
                    self.valkey_client.delete(f"planning:plans:story:{story_id}")

                self.valkey_client.delete(f"planning:plan:{plan_id}")
                self.valkey_client.srem("planning:plans:all", plan_id)

        if self.neo4j_driver:
            for task_id in self.task_ids + self.async_task_ids:
                await asyncio.to_thread(self._delete_task_node, task_id)

        if self.planning_stub:
            await self._delete_entities_with_grpc()

    def _delete_task_node(self, task_id: str) -> None:
        """Delete one task node from Neo4j graph."""
        if not self.neo4j_driver:
            return
        with self.neo4j_driver.session() as session:
            session.run("MATCH (t:Task {id: $task_id}) DETACH DELETE t", task_id=task_id)

    async def _delete_entities_with_grpc(self) -> None:
        """Delete hierarchy entities created by the test."""
        story_ids = [story_id for story_id in (self.story_id, self.async_story_id) if story_id]
        for story_id in story_ids:
            try:
                await self.planning_stub.DeleteStory(
                    planning_pb2.DeleteStoryRequest(story_id=story_id)
                )
            except Exception as exc:  # pragma: no cover - cleanup best effort
                print_warning(f"DeleteStory cleanup failed ({story_id}): {exc}")

        if self.epic_id:
            try:
                await self.planning_stub.DeleteEpic(
                    planning_pb2.DeleteEpicRequest(epic_id=self.epic_id)
                )
            except Exception as exc:  # pragma: no cover - cleanup best effort
                print_warning(f"DeleteEpic cleanup failed: {exc}")

        if self.project_id:
            try:
                await self.planning_stub.DeleteProject(
                    planning_pb2.DeleteProjectRequest(project_id=self.project_id)
                )
            except Exception as exc:  # pragma: no cover - cleanup best effort
                print_warning(f"DeleteProject cleanup failed: {exc}")

    async def step_1_create_project_epic_story(self) -> bool:
        """Create hierarchy data required for task creation validation."""
        print_step(1, "Create project, epic and story")

        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        try:
            project_resp = await self.planning_stub.CreateProject(
                planning_pb2.CreateProjectRequest(
                    name="E2E Task Derivation Project",
                    description="Temporary project for task derivation gRPC E2E",
                    owner=self.created_by,
                )
            )
            if not project_resp.success:
                print_error(f"CreateProject failed: {project_resp.message}")
                return False
            self.project_id = project_resp.project.project_id

            epic_resp = await self.planning_stub.CreateEpic(
                planning_pb2.CreateEpicRequest(
                    project_id=self.project_id,
                    title="E2E Task Derivation Epic",
                    description="Temporary epic for task derivation gRPC E2E",
                )
            )
            if not epic_resp.success:
                print_error(f"CreateEpic failed: {epic_resp.message}")
                return False
            self.epic_id = epic_resp.epic.epic_id

            story_resp = await self.planning_stub.CreateStory(
                planning_pb2.CreateStoryRequest(
                    epic_id=self.epic_id,
                    title=self.story_title,
                    brief="Validate TaskDerivationPlanningService contract end-to-end",
                    created_by=self.created_by,
                )
            )
            if not story_resp.success:
                print_error(f"CreateStory failed: {story_resp.message}")
                return False
            self.story_id = story_resp.story.story_id

            print_success(
                f"Created hierarchy: project={self.project_id}, epic={self.epic_id}, story={self.story_id}"
            )
            return True

        except grpc.RpcError as exc:
            print_error(f"gRPC error while creating hierarchy: {exc.code()} - {exc.details()}")
            return False
        except Exception as exc:
            print_error(f"Unexpected error while creating hierarchy: {exc}")
            return False

    async def step_2_seed_plan_context_in_valkey(self) -> bool:
        """Seed plan snapshot in Valkey to drive GetPlanContext RPC."""
        print_step(2, "Seed plan context in Valkey")

        if not self.story_id or not self.valkey_client:
            print_error("Story ID or Valkey client not available")
            return False

        try:
            self._seed_plan_in_valkey(
                plan_id=self.plan_id,
                story_id=self.story_id,
                title="E2E Task Derivation Plan",
                description="Plan context seeded by E2E test",
                acceptance_criteria=(
                    "Expose TaskDerivationPlanningService",
                    "Persist and list derived tasks",
                ),
                technical_notes="Contract validation path",
                roles=("DEV", "QA"),
            )

            print_success(f"Plan seeded in Valkey with plan_id={self.plan_id}")
            return True

        except Exception as exc:
            print_error(f"Failed to seed plan in Valkey: {exc}")
            return False

    def _seed_plan_in_valkey(
        self,
        *,
        plan_id: str,
        story_id: str,
        title: str,
        description: str,
        acceptance_criteria: tuple[str, ...],
        technical_notes: str,
        roles: tuple[str, ...],
    ) -> None:
        """Persist a plan snapshot in Valkey (source of truth for GetPlanContext)."""
        if not self.valkey_client:
            raise ValueError("Valkey client not initialized")

        plan_hash_key = f"planning:plan:{plan_id}"
        plans_by_story_key = f"planning:plans:story:{story_id}"

        self.valkey_client.hset(
            plan_hash_key,
            mapping={
                "plan_id": plan_id,
                "story_ids": json.dumps([story_id]),
                "title": title,
                "description": description,
                "acceptance_criteria": json.dumps(list(acceptance_criteria)),
                "technical_notes": technical_notes,
                "roles": json.dumps(list(roles)),
            },
        )
        self.valkey_client.sadd("planning:plans:all", plan_id)
        self.valkey_client.sadd(plans_by_story_key, plan_id)

    async def step_3_get_plan_context(self) -> bool:
        """Validate GetPlanContext RPC."""
        print_step(3, "Validate GetPlanContext RPC")

        if not self.task_derivation_stub or not self.story_id:
            print_error("Task derivation stub or story ID not available")
            return False

        try:
            response = await self.task_derivation_stub.GetPlanContext(
                task_derivation_pb2.GetPlanContextRequest(plan_id=self.plan_id)
            )

            context = response.plan_context
            if context.plan_id != self.plan_id:
                print_error(f"Unexpected plan_id in context: {context.plan_id}")
                return False
            if context.story_id != self.story_id:
                print_error(f"Unexpected story_id in context: {context.story_id}")
                return False
            if not context.acceptance_criteria:
                print_error("acceptance_criteria is empty")
                return False

            print_success(
                f"GetPlanContext OK: plan_id={context.plan_id}, story_id={context.story_id}"
            )
            return True

        except grpc.RpcError as exc:
            print_error(f"GetPlanContext RPC failed: {exc.code()} - {exc.details()}")
            return False
        except Exception as exc:
            print_error(f"Unexpected error in GetPlanContext: {exc}")
            return False

    async def step_4_create_tasks(self) -> bool:
        """Validate CreateTasks RPC."""
        print_step(4, "Validate CreateTasks RPC")

        if not self.task_derivation_stub or not self.story_id:
            print_error("Task derivation stub or story ID not available")
            return False

        try:
            response = await self.task_derivation_stub.CreateTasks(
                task_derivation_pb2.CreateTasksRequest(
                    commands=[
                        task_derivation_pb2.TaskCreationCommand(
                            plan_id=self.plan_id,
                            story_id=self.story_id,
                            title="Implement API endpoint",
                            description="Implement gRPC endpoint behavior",
                            estimated_hours=3,
                            priority=1,
                            assigned_role="DEV",
                        ),
                        task_derivation_pb2.TaskCreationCommand(
                            plan_id=self.plan_id,
                            story_id=self.story_id,
                            title="Add contract tests",
                            description="Validate all Task Derivation RPCs",
                            estimated_hours=2,
                            priority=2,
                            assigned_role="QA",
                        ),
                    ]
                )
            )

            self.task_ids = list(response.task_ids)
            if len(self.task_ids) != 2 or any(not task_id for task_id in self.task_ids):
                print_error(f"CreateTasks returned invalid task_ids: {self.task_ids}")
                return False

            print_success(f"CreateTasks OK: task_ids={self.task_ids}")
            return True

        except grpc.RpcError as exc:
            print_error(f"CreateTasks RPC failed: {exc.code()} - {exc.details()}")
            return False
        except Exception as exc:
            print_error(f"Unexpected error in CreateTasks: {exc}")
            return False

    async def step_5_list_story_tasks(self) -> bool:
        """Validate ListStoryTasks RPC."""
        print_step(5, "Validate ListStoryTasks RPC")

        if not self.task_derivation_stub or not self.story_id:
            print_error("Task derivation stub or story ID not available")
            return False

        try:
            response = await self.task_derivation_stub.ListStoryTasks(
                task_derivation_pb2.ListStoryTasksRequest(story_id=self.story_id)
            )
            returned_ids = {task.task_id for task in response.tasks}
            expected_ids = set(self.task_ids)

            if not expected_ids.issubset(returned_ids):
                print_error(
                    f"ListStoryTasks missing expected IDs. expected={expected_ids}, returned={returned_ids}"
                )
                return False

            print_success(f"ListStoryTasks OK: returned {len(response.tasks)} tasks")
            return True

        except grpc.RpcError as exc:
            print_error(f"ListStoryTasks RPC failed: {exc.code()} - {exc.details()}")
            return False
        except Exception as exc:
            print_error(f"Unexpected error in ListStoryTasks: {exc}")
            return False

    async def step_6_save_task_dependencies(self) -> bool:
        """Validate SaveTaskDependencies RPC."""
        print_step(6, "Validate SaveTaskDependencies RPC")

        if not self.task_derivation_stub or not self.story_id or len(self.task_ids) < 2:
            print_error("Prerequisites not met for SaveTaskDependencies")
            return False

        try:
            response = await self.task_derivation_stub.SaveTaskDependencies(
                task_derivation_pb2.SaveTaskDependenciesRequest(
                    plan_id=self.plan_id,
                    story_id=self.story_id,
                    edges=[
                        task_derivation_pb2.DependencyEdge(
                            from_task_id=self.task_ids[0],
                            to_task_id=self.task_ids[1],
                            reason="Execution order",
                        )
                    ],
                )
            )

            if not response.success:
                print_error("SaveTaskDependencies returned success=false")
                return False

            print_success("SaveTaskDependencies OK")
            return True

        except grpc.RpcError as exc:
            print_error(f"SaveTaskDependencies RPC failed: {exc.code()} - {exc.details()}")
            return False
        except Exception as exc:
            print_error(f"Unexpected error in SaveTaskDependencies: {exc}")
            return False

    async def step_7_verify_dependency_in_neo4j(self) -> bool:
        """Verify dependency edge persisted in Neo4j."""
        print_step(7, "Verify dependency edge in Neo4j")

        if not self.neo4j_driver or len(self.task_ids) < 2:
            print_error("Neo4j driver or task IDs not available")
            return False

        try:
            reason = await self._fetch_dependency_reason_with_retry(
                from_task_id=self.task_ids[0],
                to_task_id=self.task_ids[1],
                retries=5,
                delay_seconds=1.0,
            )
            if reason is None:
                print_error("No DEPENDS_ON relationship found in Neo4j")
                return False
            if reason != "Execution order":
                print_error(f"Unexpected dependency reason: {reason}")
                return False

            print_success("Neo4j dependency verified")
            return True

        except Exception as exc:
            print_error(f"Failed to verify dependency in Neo4j: {exc}")
            return False

    async def step_8_prepare_async_derivation_case(self) -> bool:
        """Create isolated story+plan used for async vLLM derivation validation."""
        print_step(8, "Prepare async derivation case")

        if not self.planning_stub or not self.epic_id or not self.valkey_client:
            print_error("Planning stub, epic_id or valkey client not available")
            return False

        try:
            story_resp = await self.planning_stub.CreateStory(
                planning_pb2.CreateStoryRequest(
                    epic_id=self.epic_id,
                    title=self.async_story_title,
                    brief="Story used to validate planning.plan.approved -> vLLM derivation",
                    created_by=self.created_by,
                )
            )
            if not story_resp.success:
                print_error(f"CreateStory for async case failed: {story_resp.message}")
                return False

            self.async_story_id = story_resp.story.story_id
            self._seed_plan_in_valkey(
                plan_id=self.async_plan_id,
                story_id=self.async_story_id,
                title="E2E Async Plan Approval",
                description="Plan for validating automatic task derivation via vLLM",
                acceptance_criteria=(
                    "When plan is approved, derivation request is emitted",
                    "Derived tasks are persisted in planning with plan_id",
                ),
                technical_notes="Event-driven derivation path",
                roles=("DEVELOPER", "QA"),
            )

            existing = await self._list_tasks_for_story(self.async_story_id)
            if existing:
                print_warning(
                    f"Async story already has {len(existing)} tasks before trigger (expected 0)"
                )

            print_success(
                f"Prepared async case: story={self.async_story_id}, plan={self.async_plan_id}"
            )
            return True

        except grpc.RpcError as exc:
            print_error(
                f"gRPC error while preparing async derivation case: {exc.code()} - {exc.details()}"
            )
            return False
        except Exception as exc:
            print_error(f"Unexpected error while preparing async derivation case: {exc}")
            return False

    async def step_9_validate_async_consumers(self) -> bool:
        """Verify required consumers are registered in JetStream."""
        print_step(9, "Validate async consumers")

        if not self.jetstream:
            print_error("JetStream not initialized")
            return False

        try:
            await self.jetstream.consumer_info(
                "PLANNING_EVENTS",
                "planning-task-derivation-consumer",
            )
            await self.jetstream.consumer_info(
                "task_derivation",
                "task-derivation-request-consumer",
            )

            print_success(
                "Consumers found: planning-task-derivation-consumer and "
                "task-derivation-request-consumer"
            )
            return True

        except Exception as exc:
            print_error(f"Required consumers not available in JetStream: {exc}")
            return False

    async def step_10_publish_plan_approved_event(self) -> bool:
        """Publish planning.plan.approved envelope to trigger derivation pipeline."""
        print_step(10, "Publish planning.plan.approved event")

        if not self.jetstream or not self.async_story_id:
            print_error("JetStream or async story ID not available")
            return False

        try:
            payload = {
                "ceremony_id": f"E2E-CER-{int(time.time())}",
                "story_id": self.async_story_id,
                "plan_id": self.async_plan_id,
                "approved_by": self.created_by,
                "approved_at": datetime.now(UTC).isoformat(),
                "tasks_outline": [],
                "estimated_complexity": "MEDIUM",
                "tasks_created": 0,
                "tasks_updated": 0,
                "po_notes": "E2E trigger for async derivation",
                "po_concerns": "",
                "priority_adjustment": "",
                "po_priority_reason": "",
            }
            envelope = self._build_event_envelope(
                event_type="planning.plan.approved",
                payload=payload,
                producer="e2e-task-derivation-test",
            )

            await self.jetstream.publish(
                "planning.plan.approved",
                json.dumps(envelope).encode("utf-8"),
            )

            print_success(
                f"Published planning.plan.approved for plan={self.async_plan_id}, story={self.async_story_id}"
            )
            return True

        except Exception as exc:
            print_error(f"Failed to publish planning.plan.approved event: {exc}")
            return False

    async def step_11_wait_for_derived_tasks(self) -> bool:
        """Wait until async pipeline persists tasks derived through vLLM."""
        print_step(11, "Wait for derived tasks (Ray/vLLM pipeline)")

        if not self.async_story_id:
            print_error("Async story ID not available")
            return False

        start = time.time()
        attempts = 0

        while time.time() - start < self.derivation_timeout:
            attempts += 1
            try:
                tasks = await self._list_tasks_for_story(self.async_story_id)
            except Exception as exc:
                print_warning(f"ListTasks polling failed (attempt {attempts}): {exc}")
                await asyncio.sleep(self.derivation_poll_interval)
                continue

            plan_tasks = [task for task in tasks if task.plan_id == self.async_plan_id]
            self.async_task_ids = [task.task_id for task in plan_tasks]
            self.async_task_types = {task.task_id: task.type for task in plan_tasks}

            development_tasks = [
                task
                for task in plan_tasks
                if (task.type or "").upper() == "DEVELOPMENT"
            ]

            if development_tasks:
                print_success(
                    f"Derived tasks persisted: {len(plan_tasks)} for plan {self.async_plan_id}"
                )
                print_success(
                    f"Found {len(development_tasks)} DEVELOPMENT task(s) created by async derivation"
                )
                return True

            elapsed = int(time.time() - start)
            print_info(
                f"Polling async derivation (attempt {attempts}, {elapsed}s elapsed): "
                f"{len(plan_tasks)} task(s) with plan_id={self.async_plan_id}"
            )
            await asyncio.sleep(self.derivation_poll_interval)

        print_error(
            "Timeout waiting for derived tasks. "
            f"plan_id={self.async_plan_id}, observed_tasks={len(self.async_task_ids)}"
        )
        if self.async_task_types:
            print_error(f"Observed task types: {self.async_task_types}")
        return False

    async def _list_tasks_for_story(self, story_id: str) -> list[Any]:
        """List all tasks for a story via PlanningService."""
        if not self.planning_stub:
            raise ValueError("Planning stub not initialized")

        response = await self.planning_stub.ListTasks(
            planning_pb2.ListTasksRequest(
                story_id=story_id,
                limit=1000,
                offset=0,
            )
        )
        if not response.success:
            raise RuntimeError(f"ListTasks failed: {response.message}")
        return list(response.tasks)

    @staticmethod
    def _build_event_envelope(
        *,
        event_type: str,
        payload: dict[str, Any],
        producer: str,
    ) -> dict[str, Any]:
        """Build EventEnvelope dict compatible with parse_required_envelope()."""
        return {
            "event_type": event_type,
            "payload": payload,
            "idempotency_key": f"e2e-{uuid4()}",
            "correlation_id": f"e2e-corr-{uuid4()}",
            "timestamp": datetime.now(UTC).isoformat(),
            "producer": producer,
            "metadata": {"source": "e2e"},
        }

    async def _fetch_dependency_reason_with_retry(
        self,
        *,
        from_task_id: str,
        to_task_id: str,
        retries: int,
        delay_seconds: float,
    ) -> str | None:
        """Fetch dependency reason with retries for eventual consistency."""
        for attempt in range(1, retries + 1):
            reason = await asyncio.to_thread(
                self._fetch_dependency_reason,
                from_task_id,
                to_task_id,
            )
            if reason is not None:
                return reason
            if attempt < retries:
                await asyncio.sleep(delay_seconds)
        return None

    def _fetch_dependency_reason(self, from_task_id: str, to_task_id: str) -> str | None:
        """Fetch dependency reason from Neo4j."""
        if not self.neo4j_driver:
            return None
        query = (
            "MATCH (f:Task {id: $from_task_id})-[r:DEPENDS_ON]->(t:Task {id: $to_task_id}) "
            "RETURN r.reason AS reason"
        )
        with self.neo4j_driver.session() as session:
            result = session.run(
                query,
                from_task_id=from_task_id,
                to_task_id=to_task_id,
            )
            record = result.single()
            return record["reason"] if record else None

    async def run(self) -> int:
        """Run all E2E steps."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}TaskDerivationPlanningService E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning URL: {self.planning_service_url}")
        print(f"  Valkey: {self.valkey_host}:{self.valkey_port}")
        print(f"  NATS: {self.nats_url}")
        print(f"  Neo4j: {self.neo4j_uri}")
        print(f"  Plan ID: {self.plan_id}")
        print(f"  Async Plan ID: {self.async_plan_id}")
        print(f"  Derivation Timeout: {self.derivation_timeout}s")
        print()

        try:
            await self.setup()

            steps: list[tuple[str, Any]] = [
                ("Create hierarchy", self.step_1_create_project_epic_story),
                ("Seed plan context", self.step_2_seed_plan_context_in_valkey),
                ("GetPlanContext", self.step_3_get_plan_context),
                ("CreateTasks", self.step_4_create_tasks),
                ("ListStoryTasks", self.step_5_list_story_tasks),
                ("SaveTaskDependencies", self.step_6_save_task_dependencies),
                ("Verify dependency in Neo4j", self.step_7_verify_dependency_in_neo4j),
                ("Prepare async derivation case", self.step_8_prepare_async_derivation_case),
                ("Validate async consumers", self.step_9_validate_async_consumers),
                ("Publish planning.plan.approved", self.step_10_publish_plan_approved_event),
                ("Wait for derived tasks", self.step_11_wait_for_derived_tasks),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step failed: {step_name}")
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(
                f"{Colors.GREEN}PASS: Contract RPCs + async vLLM derivation "
                "validated end-to-end"
                f"{Colors.NC}"
            )
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print_warning("Test interrupted by user")
            return 130
        except Exception as exc:
            print_error(f"Unexpected error: {exc}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            await self.cleanup()


async def main() -> int:
    """Main entrypoint."""
    test = TaskDerivationPlanningServiceE2E()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
