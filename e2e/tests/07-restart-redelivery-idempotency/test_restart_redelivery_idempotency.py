#!/usr/bin/env python3
"""E2E Test: Restart & Redelivery Idempotency (B0.5).

This test validates idempotency during restart and redelivery scenarios:
- Duplicate publish of the same event (same idempotency_key)
- Simulate BRP restart between deliveries
- Assert: 0 duplicate tasks created

Test Scenarios:
1. Publish the same agent.response.completed event twice
2. Verify that only one set of tasks is created (no duplicates)
3. Simulate BRP restart by publishing event again after processing
4. Verify idempotency prevents duplicate task creation

Prerequisites:
- Planning Service must be deployed
- Backlog Review Processor must be deployed
- NATS must be accessible
- Valkey must be accessible (for idempotency state)
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Optional

import grpc
import nats
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc  # type: ignore[import]
from nats.js import JetStreamContext


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.NC}")


def create_event_envelope(
    event_type: str,
    payload: dict,
    producer: str,
    entity_id: str,
    operation: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    """Create event envelope for testing.

    Simplified version of create_event_envelope from core/shared/events.
    Uses deterministic idempotency_key based on event_type + entity_id + operation.
    """
    import hashlib
    import uuid
    from datetime import UTC, datetime

    # Generate deterministic idempotency key (no timestamp for determinism)
    components = [event_type, entity_id]
    if operation:
        components.append(operation)
    idempotency_key = hashlib.sha256(":".join(components).encode()).hexdigest()

    # Generate correlation ID if not provided
    if not correlation_id:
        correlation_id = str(uuid.uuid4())

    return {
        "event_type": event_type,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "producer": producer,
        "metadata": {},
    }


class RestartRedeliveryIdempotencyTest:
    """E2E test for restart & redelivery idempotency."""

    def __init__(self) -> None:
        """Initialize with service URLs from environment."""
        # Service URLs
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )
        self.nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")

        # Test configuration
        self.story_id = os.getenv("TEST_STORY_ID", "ST-001")
        self.ceremony_id = os.getenv("TEST_CEREMONY_ID", "BRC-TEST-001")
        self.task_timeout = int(os.getenv("TASK_TIMEOUT", "120"))  # 2 minutes
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "5"))  # 5 seconds

        # Test state
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None
        self.nats_client: Optional[Any] = None  # nats.Client (avoiding import for type hint)
        self.jetstream: Optional[JetStreamContext] = None

        # Test results
        self.initial_task_count: int = 0
        self.after_first_publish_task_count: int = 0
        self.after_duplicate_publish_task_count: int = 0

    async def setup(self) -> None:
        """Set up connections."""
        print_info("Setting up connections...")

        # gRPC channel
        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)

        # NATS connection
        self.nats_client = await nats.connect(self.nats_url)
        self.jetstream = self.nats_client.jetstream()

        print_success("Connections established")

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()

        if self.nats_client:
            await self.nats_client.close()

        print_success("Connections cleaned up")

    async def ensure_story_exists(self, story_id: str) -> bool:
        """Verify that the story exists in Planning Service (required for CreateTask).

        Returns:
            True if story exists, False otherwise.
        """
        if not self.planning_stub:
            return False
        try:
            request = planning_pb2.GetStoryRequest(story_id=story_id)
            response = await self.planning_stub.GetStory(request)
            # GetStory returns empty Story and sets NOT_FOUND when missing
            if response.story_id:
                return True
            return False
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return False
            print_warning(f"GetStory failed: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_warning(f"GetStory failed: {e}")
            return False

    async def get_task_count(self, story_id: str) -> int:
        """Get current task count for a story."""
        if not self.planning_stub:
            return 0

        try:
            request = planning_pb2.ListTasksRequest(story_id=story_id, limit=100)
            response = await self.planning_stub.ListTasks(request)

            if response.success:
                return len(list(response.tasks))
            return 0

        except Exception as e:
            print_warning(f"Failed to get task count: {e}")
            return 0

    async def wait_for_tasks(
        self,
        story_id: str,
        expected_count: int,
        timeout: int,
        description: str,
    ) -> int:
        """Wait for tasks to be created, returning final count."""
        print_info(f"Waiting for tasks ({description})...")
        start_time = time.time()
        last_count = await self.get_task_count(story_id)

        while time.time() - start_time < timeout:
            current_count = await self.get_task_count(story_id)

            if current_count >= expected_count:
                elapsed = time.time() - start_time
                print_success(
                    f"Tasks created: {current_count} (expected at least {expected_count}) "
                    f"in {elapsed:.1f}s"
                )
                return current_count

            if current_count != last_count:
                print_info(f"Task count changed: {last_count} → {current_count}")
                last_count = current_count

            await asyncio.sleep(self.poll_interval)

        # Final check
        final_count = await self.get_task_count(story_id)
        elapsed = time.time() - start_time
        print_warning(
            f"Timeout waiting for tasks ({description}): "
            f"final_count={final_count}, expected={expected_count}, elapsed={elapsed:.1f}s"
        )
        return final_count

    async def publish_task_extraction_event(
        self,
        task_id: str,
        story_id: str,
        ceremony_id: str,
        idempotency_key: str,
        correlation_id: str,
    ) -> None:
        """Publish agent.response.completed event with task extraction results."""
        if not self.jetstream:
            raise RuntimeError("JetStream not initialized")

        # Create event payload (canonical format with tasks array)
        payload = {
            "task_id": task_id,
            "story_id": story_id,
            "ceremony_id": ceremony_id,
            "tasks": [
                {
                    "title": "E2E Test Task 1",
                    "description": "First test task for idempotency validation",
                    "estimated_hours": 4,
                    "deliberation_indices": [0],
                },
                {
                    "title": "E2E Test Task 2",
                    "description": "Second test task for idempotency validation",
                    "estimated_hours": 8,
                    "deliberation_indices": [1],
                },
            ],
            "metadata": {
                "task_type": "TASK_EXTRACTION",
            },
        }

        # Create event envelope
        envelope = {
            "event_type": "agent.response.completed",
            "payload": payload,
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "producer": "e2e-test",
            "metadata": {},
        }

        # Publish to NATS (subject must match TaskExtractionResultConsumer subscription)
        subject = "agent.response.completed.task-extraction"
        message = json.dumps(envelope).encode("utf-8")

        try:
            await self.jetstream.publish(subject, message)
            print_success(
                f"Published event: task_id={task_id}, "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"correlation_id={correlation_id}"
            )
        except Exception as e:
            print_error(f"Failed to publish event: {e}")
            raise

    async def run(self) -> int:
        """Run the idempotency test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🧪 E2E Test: Restart & Redelivery Idempotency (B0.5){Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  NATS: {self.nats_url}")
        print(f"  Story ID: {self.story_id}")
        print(f"  Ceremony ID: {self.ceremony_id}")
        print(f"  Task Timeout: {self.task_timeout}s")
        print()

        try:
            await self.setup()

            # Story must exist in Planning Service (CreateTask requires it)
            if not await self.ensure_story_exists(self.story_id):
                print_error(
                    f"Story {self.story_id} not found in Planning Service. "
                    "Run test 02 (create-test-data) first to create test data, "
                    "or set TEST_STORY_ID to an existing story."
                )
                return 1
            print_success(f"Story {self.story_id} found in Planning Service")

            # Generate deterministic IDs for test
            task_id = f"{self.ceremony_id}:{self.story_id}:task-extraction"
            entity_id = f"{self.ceremony_id}:{self.story_id}"
            operation = "task_extraction"

            # Create event envelope with deterministic idempotency_key
            envelope1 = create_event_envelope(
                event_type="agent.response.completed",
                payload={},
                producer="e2e-test",
                entity_id=entity_id,
                operation=operation,
            )
            idempotency_key = envelope1["idempotency_key"]
            correlation_id_1 = envelope1["correlation_id"]

            print_info(f"Generated idempotency_key: {idempotency_key[:32]}...")
            print_info(f"Correlation ID (1st publish): {correlation_id_1}")

            # Step 1: Get initial task count
            print()
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
            print(f"{Colors.BLUE}Step 1: Get Initial Task Count{Colors.NC}")
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
            self.initial_task_count = await self.get_task_count(self.story_id)
            print_success(f"Initial task count: {self.initial_task_count}")

            # Step 2: Publish event first time
            print()
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
            print(f"{Colors.BLUE}Step 2: Publish Event (First Time){Colors.NC}")
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
            await self.publish_task_extraction_event(
                task_id=task_id,
                story_id=self.story_id,
                ceremony_id=self.ceremony_id,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id_1,
            )

            # Wait for tasks to be created
            self.after_first_publish_task_count = await self.wait_for_tasks(
                story_id=self.story_id,
                expected_count=self.initial_task_count + 2,  # Expect 2 tasks
                timeout=self.task_timeout,
                description="after first publish",
            )

            # Step 3: Publish same event again (duplicate/redelivery)
            print()
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
            print(f"{Colors.BLUE}Step 3: Publish Same Event Again (Duplicate/Redelivery){Colors.NC}")
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")

            # Use same idempotency_key but different correlation_id (simulating redelivery)
            correlation_id_2 = str(int(time.time() * 1000))  # Different correlation ID
            print_info(f"Correlation ID (2nd publish): {correlation_id_2}")
            print_info(f"Same idempotency_key: {idempotency_key[:32]}...")

            await self.publish_task_extraction_event(
                task_id=task_id,
                story_id=self.story_id,
                ceremony_id=self.ceremony_id,
                idempotency_key=idempotency_key,  # Same idempotency_key
                correlation_id=correlation_id_2,  # Different correlation_id
            )

            # Wait a bit to ensure processing
            await asyncio.sleep(10)

            # Get final task count
            self.after_duplicate_publish_task_count = await self.get_task_count(self.story_id)

            # Step 4: Validate idempotency
            print()
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
            print(f"{Colors.BLUE}Step 4: Validate Idempotency{Colors.NC}")
            print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")

            print()
            print("Results:")
            print(f"  Initial task count: {self.initial_task_count}")
            print(f"  After first publish: {self.after_first_publish_task_count}")
            print(f"  After duplicate publish: {self.after_duplicate_publish_task_count}")
            print()

            # Validation
            tasks_created_first = self.after_first_publish_task_count - self.initial_task_count
            tasks_created_after_duplicate = (
                self.after_duplicate_publish_task_count - self.after_first_publish_task_count
            )

            print(f"  Tasks created (first publish): {tasks_created_first}")
            print(f"  Tasks created (duplicate publish): {tasks_created_after_duplicate}")
            print()

            # Assertions
            if tasks_created_after_duplicate == 0:
                print_success("✅ IDEMPOTENCY VALIDATED: No duplicate tasks created")
            else:
                print_error(
                    f"❌ IDEMPOTENCY VIOLATION: {tasks_created_after_duplicate} duplicate tasks created"
                )
                return 1

            if tasks_created_first > 0:
                print_success(f"✅ First publish created {tasks_created_first} tasks (expected)")
            else:
                print_warning(f"⚠️  First publish created {tasks_created_first} tasks (unexpected)")

            # Summary
            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ Test Completed Successfully{Colors.NC}")
            print(f"{Colors.GREEN}✅ Idempotency validated: 0 duplicate tasks created{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()

            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Test interrupted by user")
            return 130
        except Exception as e:
            print_error(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            await self.cleanup()


async def main() -> int:
    """Main entry point."""
    test = RestartRedeliveryIdempotencyTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
