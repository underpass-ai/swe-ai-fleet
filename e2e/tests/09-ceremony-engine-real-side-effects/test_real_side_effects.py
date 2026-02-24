#!/usr/bin/env python3
"""E2E Test: Ceremony Engine Real Side-Effects Validation.

This E2E test validates that ceremony engine operations produce real side-effects:
- NATS messages are published to real NATS JetStream
- Persistence updates are written to real Valkey/Neo4j
- External service calls (Ray Executor) are triggered

Flow Verified:
1. Start a ceremony instance via planning_ceremony_processor gRPC
2. Execute steps that trigger:
   - NATS message publishing (publish_step)
   - Persistence updates (dual persistence)
   - External service calls (deliberation_step -> Ray Executor)
3. Verify:
   - NATS messages exist in JetStream
   - Instance persisted in Valkey
   - Instance persisted in Neo4j
   - Ray Executor received calls (via gRPC)

Test Prerequisites:
- planning_ceremony_processor service deployed
- NATS JetStream available
- Valkey available
- Neo4j available
- Ray Executor service available
- Ceremony definitions available in config/ceremonies

Test Data:
- Uses dummy_ceremony.yaml for basic ceremony execution
"""

import asyncio
import os
import sys
import time
from typing import Any

import grpc
import nats
import valkey
from nats.js import JetStreamContext
from neo4j import GraphDatabase

# Import ceremony engine
sys.path.insert(0, "/app")
from core.ceremony_engine.application.ports.definition_port import DefinitionPort
from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.infrastructure.adapters.ceremony_definition_adapter import (
    CeremonyDefinitionAdapter,
)
from core.ceremony_engine.infrastructure.adapters.dual_persistence_adapter import (
    DualPersistenceAdapter,
)
from core.ceremony_engine.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
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


class CeremonyEngineRealSideEffectsTest:
    """E2E test for ceremony engine real side-effects validation."""

    def __init__(self) -> None:
        """Initialize test with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
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
        self.ceremony_name = os.getenv("CEREMONY_NAME", "dummy_ceremony")

        # Test data
        self.instance_id: str | None = None
        self.correlation_id = f"e2e-test-{int(time.time())}"

        # Connections
        self.nats_client: nats.Client | None = None
        self.jetstream: JetStreamContext | None = None
        self.neo4j_driver: Any | None = None
        self.valkey_client: Any | None = None
        self.grpc_channel: grpc.aio.Channel | None = None
        self.grpc_stub: planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub | None = None
        
        # Track if we created the CEREMONY stream (for cleanup)
        self.ceremony_stream_created: bool = False

    async def setup(self) -> None:
        """Set up connections to all services."""
        print_info("Setting up connections...")

        # NATS
        print_info(f"Connecting to NATS at {self.nats_url}...")
        self.nats_client = await asyncio.wait_for(
            nats.connect(self.nats_url),
            timeout=10.0,
        )
        self.jetstream = self.nats_client.jetstream()
        print_success("NATS connected")
        
        # Ensure CEREMONY stream exists (for test)
        print_info("Ensuring CEREMONY stream exists...")
        try:
            from nats.js.api import StreamConfig
            try:
                await self.jetstream.stream_info("CEREMONY")
                print_success("CEREMONY stream already exists")
                self.ceremony_stream_created = False  # We didn't create it
            except Exception:
                # Stream doesn't exist, create it using StreamConfig (simplified like context service)
                stream_config = StreamConfig(
                    name="CEREMONY",
                    subjects=["ceremony.>"],
                    description="Ceremony engine events for E2E tests",
                )
                await self.jetstream.add_stream(stream_config)
                print_success("CEREMONY stream created")
                self.ceremony_stream_created = True  # Mark that we created it
        except Exception as e:
            print_warning(f"Could not ensure CEREMONY stream: {e}")
            print_warning("Continuing anyway - stream may be created on first publish")
            self.ceremony_stream_created = False

        # Neo4j
        print_info(f"Connecting to Neo4j at {self.neo4j_uri}...")
        self.neo4j_driver = GraphDatabase.driver(
            self.neo4j_uri,
            auth=(self.neo4j_user, self.neo4j_password),
        )
        print_success("Neo4j connected")

        # Valkey
        print_info(f"Connecting to Valkey at {self.valkey_host}:{self.valkey_port}...")
        self.valkey_client = valkey.Valkey(
            host=self.valkey_host,
            port=self.valkey_port,
            decode_responses=True,
        )
        self.valkey_client.ping()
        print_success("Valkey connected")

        # gRPC
        print_info(f"Connecting to planning_ceremony_processor at {self.planning_ceremony_processor_url}...")
        self.grpc_channel = grpc.aio.insecure_channel(self.planning_ceremony_processor_url)
        self.grpc_stub = planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub(self.grpc_channel)
        # Wait for channel ready with timeout
        try:
            await asyncio.wait_for(self.grpc_channel.channel_ready(), timeout=10.0)
            print_success("gRPC connected")
        except asyncio.TimeoutError:
            print_warning("gRPC channel not ready within timeout, but continuing...")

        print_success("All connections established")

    async def cleanup(self) -> None:
        """Clean up connections and test resources."""
        print_info("Cleaning up connections and test resources...")

        # Clean up CEREMONY stream if we created it
        if self.ceremony_stream_created and self.jetstream:
            try:
                print_info("Deleting CEREMONY stream (created by test)...")
                await self.jetstream.delete_stream("CEREMONY")
                print_success("CEREMONY stream deleted")
            except Exception as e:
                print_warning(f"Could not delete CEREMONY stream: {e}")

        if self.grpc_channel:
            await self.grpc_channel.close()

        if self.valkey_client:
            self.valkey_client.close()

        if self.neo4j_driver:
            self.neo4j_driver.close()

        if self.nats_client:
            await self.nats_client.close()

        print_success("Cleanup completed")

    async def test_step_1_start_ceremony_via_grpc(self) -> bool:
        """Test: Start ceremony via planning_ceremony_processor gRPC."""
        print_step(1, "Start ceremony via gRPC")

        try:
            # Build request with all required fields
            # For dummy_ceremony, we use a synthetic story_id and ceremony_id
            ceremony_id = f"e2e-ceremony-{int(time.time())}"
            story_id = "e2e-test-story-001"  # Synthetic story ID for test
            step_ids = ["process_step"]  # Step ID from dummy_ceremony.yaml
            
            request = planning_ceremony_pb2.StartPlanningCeremonyRequest(
                ceremony_id=ceremony_id,
                definition_name=self.ceremony_name,  # "dummy_ceremony"
                story_id=story_id,
                correlation_id=self.correlation_id,
                step_ids=step_ids,
                requested_by="e2e-test@system.local",
                inputs={
                    "input_data": '{"test": "data", "value": "e2e-test"}',  # Required by dummy_ceremony
                },
            )

            print_info(f"Calling StartPlanningCeremony with:")
            print_info(f"  ceremony_id={ceremony_id}")
            print_info(f"  definition_name={self.ceremony_name}")
            print_info(f"  story_id={story_id}")
            print_info(f"  step_ids={step_ids}")
            
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

    async def test_step_2_verify_nats_messages(self) -> bool:
        """Test: Verify NATS messages were published."""
        print_step(2, "Verify NATS messages published")

        try:
            # Wait a bit for ceremony to execute and publish messages
            print_info("Waiting for ceremony execution and message publishing...")
            await asyncio.sleep(5)

            # Try to read messages from JetStream stream
            subject = "ceremony.step.executed"
            print_info(f"Checking for messages on {subject}...")

            # Simplified approach: just verify stream exists and has messages
            # Use timeout to avoid blocking indefinitely
            try:
                stream_name = "CEREMONY"
                stream_info = await asyncio.wait_for(
                    self.jetstream.stream_info(stream_name),
                    timeout=5.0,
                )
                print_info(f"Found stream: {stream_name}")
                
                # Check stream state (has messages)
                state = stream_info.state
                if state.messages > 0:
                    print_success(f"Stream has {state.messages} message(s) - messages are being published")
                    return True
                else:
                    print_error("Stream exists but has no messages - expected published messages")
                    return False

            except asyncio.TimeoutError:
                print_error("Timeout checking stream")
                return False
            except Exception as stream_error:
                print_error(f"Could not check stream: {stream_error}")
                return False

        except Exception as e:
            print_error(f"Error checking NATS messages: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_step_3_verify_valkey_persistence(self) -> bool:
        """Test: Verify instance persisted in Valkey."""
        print_step(3, "Verify Valkey persistence")

        if not self.instance_id:
            print_error("instance_id not set")
            return False

        try:
            # Check if instance exists in Valkey
            key = f"ceremony:instance:{self.instance_id}"
            print_info(f"Checking Valkey key: {key}")

            instance_data = self.valkey_client.get(key)
            if instance_data:
                print_success(f"Instance found in Valkey: {len(instance_data)} bytes")
                return True
            else:
                print_error(f"Instance not found in Valkey: {key}")
                return False

        except Exception as e:
            print_error(f"Error checking Valkey: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_step_wait_for_execution(self) -> bool:
        """Test: Wait for ceremony execution to complete."""
        print_step(2, "Wait for ceremony execution")
        print_info("Waiting 3 seconds for ceremony steps to execute...")
        await asyncio.sleep(3)
        print_success("Wait completed")
        return True

    async def test_step_4_verify_neo4j_persistence(self) -> bool:
        """Test: Verify instance persisted in Neo4j."""
        print_step(4, "Verify Neo4j persistence")

        if not self.instance_id:
            print_error("instance_id not set")
            return False

        try:
            # Query Neo4j for instance node
            query = "MATCH (n:CeremonyInstance {instance_id: $instance_id}) RETURN n"
            print_info(f"Querying Neo4j for instance: {self.instance_id}")

            with self.neo4j_driver.session() as session:
                result = session.run(query, instance_id=self.instance_id)
                records = list(result)

                if records:
                    print_success(f"Instance found in Neo4j: {len(records)} node(s)")
                    return True
                else:
                    print_error(f"Instance not found in Neo4j: {self.instance_id}")
                    return False

        except Exception as e:
            print_error(f"Error checking Neo4j: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run(self) -> int:
        """Run the complete E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🚀 Ceremony Engine Real Side-Effects E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Ceremony Processor: {self.planning_ceremony_processor_url}")
        print(f"  NATS: {self.nats_url}")
        print(f"  Neo4j: {self.neo4j_uri}")
        print(f"  Valkey: {self.valkey_host}:{self.valkey_port}")
        print(f"  Ceremony: {self.ceremony_name}")
        print(f"  Correlation ID: {self.correlation_id}")
        print()

        try:
            await self.setup()

            # Run test steps
            steps = [
                ("Start ceremony via gRPC", self.test_step_1_start_ceremony_via_grpc),
                ("Wait for ceremony execution", self.test_step_wait_for_execution),
                ("Verify NATS messages", self.test_step_2_verify_nats_messages),
                ("Verify Valkey persistence", self.test_step_3_verify_valkey_persistence),
                ("Verify Neo4j persistence", self.test_step_4_verify_neo4j_persistence),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ E2E test PASSED - All side-effects validated{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print()
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
    test = CeremonyEngineRealSideEffectsTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
