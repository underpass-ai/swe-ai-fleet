#!/usr/bin/env python3
"""E2E Test: Planning Ceremony Processor gRPC Server Start Validation.

This E2E test validates that the planning_ceremony_processor gRPC server:
- Starts successfully and listens on port 50057
- Is accessible via Kubernetes internal DNS
- Responds to gRPC calls correctly
- Handles basic requests without errors

Flow Verified:
1. Connect to planning_ceremony_processor gRPC endpoint
2. Call StartPlanningCeremony with minimal valid request
3. Verify response contains instance_id
4. Verify gRPC call completes without errors

Test Prerequisites:
- planning_ceremony_processor service deployed and running
- gRPC server listening on port 50057
- Ceremony definitions available in config/ceremonies
- Kubernetes namespace swe-ai-fleet with proper DNS

Test Data:
- Uses dummy_ceremony.yaml for basic ceremony start
"""

import asyncio
import os
import sys
import time
import uuid

import grpc

# Import protobuf stubs
sys.path.insert(0, "/app")
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


class PlanningCeremonyProcessorGrpcStartTest:
    """E2E test for planning_ceremony_processor gRPC server start validation."""

    def __init__(self) -> None:
        """Initialize test with service URL from environment."""
        self.grpc_url = os.getenv(
            "PLANNING_CEREMONY_PROCESSOR_URL",
            "planning-ceremony-processor.swe-ai-fleet.svc.cluster.local:50057",
        )
        self.definition_name = os.getenv("CEREMONY_NAME", "dummy_ceremony")
        self.correlation_id = f"e2e-grpc-test-{int(time.time())}"
        run_id = uuid.uuid4().hex[:8]
        self.ceremony_id = os.getenv("CEREMONY_ID", f"e2e-ceremony-{run_id}")
        self.story_id = os.getenv("STORY_ID", f"e2e-story-{run_id}")
        self.requested_by = os.getenv(
            "REQUESTED_BY", "e2e-planning-ceremony-processor-grpc-start"
        )
        self.step_ids = [
            step.strip()
            for step in os.getenv("CEREMONY_STEP_IDS", "process_step").split(",")
            if step.strip()
        ]
        self.input_data = os.getenv("CEREMONY_INPUT_DATA", "e2e-input")
        self.instance_id: str = ""

        # Connections
        self.channel: grpc.aio.Channel | None = None
        self.stub: planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub | None = None

    def _build_start_request(self) -> planning_ceremony_pb2.StartPlanningCeremonyRequest:
        """Build a valid StartPlanningCeremony request for the deployed schema."""
        return planning_ceremony_pb2.StartPlanningCeremonyRequest(
            ceremony_id=self.ceremony_id,
            definition_name=self.definition_name,
            story_id=self.story_id,
            correlation_id=self.correlation_id,
            inputs={"input_data": self.input_data},
            step_ids=self.step_ids,
            requested_by=self.requested_by,
        )

    async def setup(self) -> None:
        """Set up gRPC connection."""
        print_info("Setting up gRPC connection...")
        print_info(f"Connecting to {self.grpc_url}...")

        self.channel = grpc.aio.insecure_channel(self.grpc_url)
        self.stub = planning_ceremony_pb2_grpc.PlanningCeremonyProcessorStub(self.channel)

        # Wait for channel to be ready (with timeout)
        try:
            await asyncio.wait_for(self.channel.channel_ready(), timeout=10.0)
            print_success("gRPC channel ready")
        except asyncio.TimeoutError:
            print_error("gRPC channel not ready within timeout")
            raise
        except Exception as e:
            print_error(f"Error waiting for channel ready: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.channel:
            await self.channel.close()

        print_success("Cleanup completed")

    async def test_step_1_verify_grpc_server_accessible(self) -> bool:
        """Test: Verify gRPC server is accessible."""
        print_step(1, "Verify gRPC server is accessible")

        try:
            request = self._build_start_request()
            print_info(
                "Calling StartPlanningCeremony with "
                f"ceremony_id={self.ceremony_id}, definition_name={self.definition_name}, "
                f"story_id={self.story_id}, step_ids={self.step_ids}..."
            )
            response = await self.stub.StartPlanningCeremony(request)

            if not response.instance_id:
                print_error("gRPC response missing instance_id")
                return False

            self.instance_id = response.instance_id
            print_success(f"gRPC server responded: instance_id={response.instance_id}")
            return True

        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                print_error(f"gRPC server unavailable: {e.details()}")
                print_error("This usually means the server is not running or not accessible")
                return False
            elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                print_error(f"gRPC call timed out: {e.details()}")
                return False
            else:
                print_error(f"gRPC error: {e.code()} - {e.details()}")
                return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_step_2_verify_grpc_response_format(self) -> bool:
        """Test: Verify gRPC response has correct format."""
        print_step(2, "Verify gRPC response format")

        try:
            if not self.instance_id:
                print_error("No instance_id available from step 1")
                return False

            request = planning_ceremony_pb2.GetPlanningCeremonyInstanceRequest(
                instance_id=self.instance_id
            )
            print_info(f"Calling GetPlanningCeremonyInstance for {self.instance_id}...")
            response = await self.stub.GetPlanningCeremonyInstance(request)

            # Verify response fields
            if not hasattr(response, "success"):
                print_error("Response missing success field")
                return False

            if not response.success:
                print_error(f"Response indicates failure: {response.message}")
                return False

            if not response.ceremony.instance_id:
                print_error("Response ceremony.instance_id is empty")
                return False

            if response.ceremony.definition_name != self.definition_name:
                print_error(
                    "Response definition mismatch: "
                    f"expected={self.definition_name}, got={response.ceremony.definition_name}"
                )
                return False

            print_success(
                "Response format valid: "
                f"instance_id={response.ceremony.instance_id}, "
                f"status={response.ceremony.status}"
            )
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run(self) -> int:
        """Run the complete E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🚀 Planning Ceremony Processor gRPC Start E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  gRPC URL: {self.grpc_url}")
        print(f"  Definition: {self.definition_name}")
        print(f"  Ceremony ID: {self.ceremony_id}")
        print(f"  Story ID: {self.story_id}")
        print(f"  Requested By: {self.requested_by}")
        print(f"  Step IDs: {self.step_ids}")
        print(f"  Correlation ID: {self.correlation_id}")
        print()

        try:
            await self.setup()

            # Run test steps
            steps = [
                ("Verify gRPC server accessible", self.test_step_1_verify_grpc_server_accessible),
                ("Verify gRPC response format", self.test_step_2_verify_grpc_response_format),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ E2E test PASSED - gRPC server is running and accessible{Colors.NC}")
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
    test = PlanningCeremonyProcessorGrpcStartTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
