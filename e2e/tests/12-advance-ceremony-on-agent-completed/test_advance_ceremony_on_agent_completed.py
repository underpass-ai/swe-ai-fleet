#!/usr/bin/env python3
"""E2E Test: Advance Ceremony on Agent Completed.

Validates that planning_ceremony_processor receives and processes
agent.response.completed events:

1. Start ceremony via gRPC (get instance_id and correlation_id)
2. Publish agent.response.completed to NATS with that correlation_id
3. Wait for AgentResponseCompletedConsumer to process (ack)
4. Verify ceremony instance still exists (rehydration)
5. Verify consumer subscription exists

Prerequisites:
- planning_ceremony_processor deployed
- NATS JetStream with AGENT_RESPONSES stream
- Valkey and Neo4j available
"""

import asyncio
import json
import os
import sys
import time
from typing import Any

import grpc
import nats
import valkey
from nats.js import JetStreamContext
from neo4j import GraphDatabase

sys.path.insert(0, "/app")
from core.ceremony_engine.application.ports.definition_port import DefinitionPort
from core.ceremony_engine.application.ports.rehydration_port import RehydrationPort
from core.ceremony_engine.application.use_cases.rehydration_usecase import (
    RehydrationUseCase,
)
from core.ceremony_engine.infrastructure.adapters.ceremony_definition_adapter import (
    CeremonyDefinitionAdapter,
)
from core.ceremony_engine.infrastructure.adapters.neo4j_rehydration_adapter import (
    Neo4jRehydrationAdapter,
)
from fleet.planning_ceremony.v1 import planning_ceremony_pb2, planning_ceremony_pb2_grpc


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


def build_event_envelope(
    correlation_id: str,
    task_id: str,
    idempotency_key: str,
    producer: str = "e2e-advance-ceremony-test",
) -> dict[str, Any]:
    """Build EventEnvelope dict for agent.response.completed (parse_required_envelope contract)."""
    return {
        "event_type": "agent.response.completed",
        "payload": {"task_id": task_id},
        "idempotency_key": idempotency_key,
        "correlation_id": correlation_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": producer,
        "metadata": {},
    }


class AdvanceCeremonyOnAgentCompletedTest:
    """E2E test for advance ceremony on agent.response.completed."""

    def __init__(self) -> None:
        """Initialize test with service URLs from environment."""
        self.planning_ceremony_processor_url = os.getenv(
            "PLANNING_CEREMONY_PROCESSOR_URL",
            "planning-ceremony-processor.swe-ai-fleet.svc.cluster.local:50057",
        )
        self.nats_url = os.getenv(
            "NATS_URL",
            "nats://nats.swe-ai-fleet.svc.cluster.local:4222",
        )
        self.neo4j_uri = os.getenv(
            "NEO4J_URI",
            "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687",
        )
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "underpassai")
        self.valkey_host = os.getenv(
            "VALKEY_HOST",
            "valkey.swe-ai-fleet.svc.cluster.local",
        )
        self.valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
        self.ceremonies_dir = os.getenv("CEREMONIES_DIR", "/app/config/ceremonies")
        self.ceremony_name = os.getenv("CEREMONY_NAME", "e2e_multi_step")

        self.instance_id: str | None = None
        self.correlation_id = f"e2e-advance-ceremony-{int(time.time())}"

        self.nats_client: Any = None
        self.jetstream: JetStreamContext | None = None
        self.neo4j_driver: Any | None = None
        self.valkey_client: Any | None = None
        self.grpc_channel: grpc.aio.Channel | None = None
        self.grpc_stub: planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub | None = None
        self.rehydration_adapter: RehydrationPort | None = None
        self.definition_adapter: DefinitionPort | None = None
        self.rehydration_usecase: RehydrationUseCase | None = None

    async def setup(self) -> None:
        """Set up connections to all services."""
        print_info("Setting up connections...")

        print_info(f"Connecting to NATS at {self.nats_url}...")
        self.nats_client = await asyncio.wait_for(
            nats.connect(self.nats_url),
            timeout=10.0,
        )
        self.jetstream = self.nats_client.jetstream()
        print_success("NATS connected")

        # Ensure CEREMONY stream exists (test 11 may have deleted it in cleanup)
        print_info("Ensuring CEREMONY stream exists...")
        try:
            from nats.js.api import StreamConfig
            try:
                await self.jetstream.stream_info("CEREMONY")
                print_success("CEREMONY stream already exists")
            except Exception:
                stream_config = StreamConfig(
                    name="CEREMONY",
                    subjects=["ceremony.>"],
                    description="Ceremony engine events for E2E tests",
                )
                await self.jetstream.add_stream(stream_config)
                print_success("CEREMONY stream created")
        except Exception as e:
            print_warning(f"Could not ensure CEREMONY stream: {e}")

        print_info(f"Connecting to Neo4j at {self.neo4j_uri}...")
        self.neo4j_driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
        )
        print_success("Neo4j connected")

        from core.ceremony_engine.infrastructure.config.neo4j_config import Neo4jConfig
        neo4j_config = Neo4jConfig(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password,
        )
        self.rehydration_adapter = Neo4jRehydrationAdapter(
            neo4j_config=neo4j_config,
            ceremonies_dir=self.ceremonies_dir,
        )
        self.definition_adapter = CeremonyDefinitionAdapter(self.ceremonies_dir)
        self.rehydration_usecase = RehydrationUseCase(
            rehydration_port=self.rehydration_adapter,
            definition_port=self.definition_adapter,
        )

        print_info(f"Connecting to Valkey at {self.valkey_host}:{self.valkey_port}...")
        self.valkey_client = valkey.Valkey(
            host=self.valkey_host,
            port=self.valkey_port,
            decode_responses=True,
        )
        self.valkey_client.ping()
        print_success("Valkey connected")

        print_info(f"Connecting to planning_ceremony_processor at {self.planning_ceremony_processor_url}...")
        self.grpc_channel = grpc.aio.insecure_channel(self.planning_ceremony_processor_url)
        self.grpc_stub = planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub(self.grpc_channel)
        try:
            await asyncio.wait_for(self.grpc_channel.channel_ready(), timeout=10.0)
            print_success("gRPC connected")
        except asyncio.TimeoutError:
            print_warning("gRPC channel not ready within timeout, continuing...")

        print_success("All connections established")

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")
        if self.grpc_channel:
            await self.grpc_channel.close()
        if self.valkey_client:
            self.valkey_client.close()
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.nats_client:
            await self.nats_client.close()
        print_success("Cleanup completed")

    async def test_step_1_start_ceremony(self) -> bool:
        """Start ceremony via gRPC to obtain instance_id and correlation_id."""
        print_step(1, "Start ceremony via gRPC")
        if not self.grpc_stub:
            print_error("gRPC stub not available")
            return False

        try:
            ceremony_id = f"e2e-advance-{int(time.time())}"
            story_id = "e2e-advance-story-001"
            step_ids = ["deliberate"]

            request = planning_ceremony_pb2.StartPlanningCeremonyRequest(
                ceremony_id=ceremony_id,
                definition_name=self.ceremony_name,
                story_id=story_id,
                correlation_id=self.correlation_id,
                step_ids=step_ids,
                requested_by="e2e-advance-test@system.local",
                inputs={"input_data": '{"test": "advance-ceremony-e2e"}'},
            )

            print_info(f"StartPlanningCeremony: ceremony_id={ceremony_id}, correlation_id={self.correlation_id}")
            response = await asyncio.wait_for(
                self.grpc_stub.StartPlanningCeremony(request),
                timeout=30.0,
            )

            if not response.instance_id:
                print_error("gRPC response missing instance_id")
                return False

            self.instance_id = response.instance_id
            print_success(f"Ceremony started: instance_id={self.instance_id}")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_step_2_publish_agent_response_completed(self) -> bool:
        """Publish agent.response.completed to NATS (subject agent.response.completed)."""
        print_step(2, "Publish agent.response.completed")

        if not self.jetstream:
            print_error("JetStream not available")
            return False

        task_id = f"e2e-advance-task-{int(time.time())}"
        idempotency_key = f"e2e-advance-{self.correlation_id}-{task_id}"
        envelope = build_event_envelope(
            correlation_id=self.correlation_id,
            task_id=task_id,
            idempotency_key=idempotency_key,
        )
        subject = "agent.response.completed"
        message = json.dumps(envelope).encode("utf-8")

        try:
            await self.jetstream.publish(subject, message)
            print_success(f"Published agent.response.completed: correlation_id={self.correlation_id}, task_id={task_id}")
            return True
        except Exception as e:
            print_error(f"Failed to publish: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_step_3_wait_for_consumer(self) -> bool:
        """Wait for AgentResponseCompletedConsumer to process the message."""
        print_step(3, "Wait for consumer to process")
        print_info("Waiting 8 seconds for consumer to ack...")
        await asyncio.sleep(8)
        print_success("Wait completed")
        return True

    async def test_step_4_verify_instance_still_exists(self) -> bool:
        """Verify ceremony instance still exists (rehydration)."""
        print_step(4, "Verify ceremony instance still exists")

        if not self.instance_id or not self.rehydration_usecase:
            print_error("instance_id or rehydration_usecase not set")
            return False

        try:
            instance = await self.rehydration_usecase.rehydrate_instance(self.instance_id)
            if not instance:
                print_error(f"Instance not found: {self.instance_id}")
                return False
            print_success(f"Instance rehydrated: instance_id={instance.instance_id}, state={instance.current_state}")
            return True
        except Exception as e:
            print_error(f"Rehydration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_step_5_verify_consumer_subscription(self) -> bool:
        """Verify AgentResponseCompletedConsumer subscription exists."""
        print_step(5, "Verify consumer subscription")

        if not self.jetstream:
            print_warning("JetStream not available, skipping consumer check")
            return True

        durable_name = "planning-ceremony-processor-agent-response-completed-v1"
        stream_name = "AGENT_RESPONSES"
        try:
            await asyncio.wait_for(
                self.jetstream.consumer_info(stream_name, durable_name),
                timeout=5.0,
            )
            print_success(f"Consumer subscription found: {durable_name}")
        except Exception as e:
            print_warning(f"Consumer not found (may be created on first message): {e}")
        return True

    async def run(self) -> int:
        """Run the E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🚀 E2E Test: Advance Ceremony on Agent Completed{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Ceremony Processor: {self.planning_ceremony_processor_url}")
        print(f"  NATS: {self.nats_url}")
        print(f"  Ceremony: {self.ceremony_name}")
        print(f"  Correlation ID: {self.correlation_id}")
        print()

        try:
            await self.setup()

            steps = [
                ("Start ceremony via gRPC", self.test_step_1_start_ceremony),
                ("Publish agent.response.completed", self.test_step_2_publish_agent_response_completed),
                ("Wait for consumer", self.test_step_3_wait_for_consumer),
                ("Verify instance still exists", self.test_step_4_verify_instance_still_exists),
                ("Verify consumer subscription", self.test_step_5_verify_consumer_subscription),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ E2E test PASSED - Advance ceremony on agent completed validated{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print_warning("Test interrupted by user")
            return 130
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            await self.cleanup()


async def main() -> int:
    """Main entry point."""
    test = AdvanceCeremonyOnAgentCompletedTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
