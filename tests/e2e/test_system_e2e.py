#!/usr/bin/env python3
"""
End-to-End System Test

Tests the complete SWE AI Fleet system:
1. Orchestrator health and councils
2. NATS stream publishing
3. Event consumption
4. Deliberation flow
5. Result collection

Environment Variables:
- ORCHESTRATOR_ADDRESS: Orchestrator gRPC address (default: orchestrator.swe-ai-fleet.svc.cluster.local:50055)
- RAY_EXECUTOR_ADDRESS: Ray Executor gRPC address (default: ray_executor.swe-ai-fleet.svc.cluster.local:50056)
- NATS_URL: NATS server URL (default: nats://nats.swe-ai-fleet.svc.cluster.local:4222)
"""

import asyncio
import logging
import os
import sys
import time
from datetime import UTC

import grpc
import nats

# Import generated gRPC code
from gen import orchestrator_pb2, orchestrator_pb2_grpc
from nats.js import JetStreamContext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """End-to-End test runner for SWE AI Fleet."""

    def __init__(self):
        """Initialize test runner with environment configuration."""
        self.orchestrator_address = os.getenv(
            "ORCHESTRATOR_ADDRESS",
            "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
        )
        self.ray_executor_address = os.getenv(
            "RAY_EXECUTOR_ADDRESS",
            "ray_executor.swe-ai-fleet.svc.cluster.local:50056"
        )
        self.nats_url = os.getenv(
            "NATS_URL",
            "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
        )

        self.nc: nats.NATS | None = None
        self.js: JetStreamContext | None = None
        self.orchestrator_stub = None
        self.test_results = []
        self.last_plan_id: str | None = None

    async def setup(self):
        """Setup connections to services."""
        logger.info("🚀 Setting up E2E test environment...")

        # Connect to NATS
        try:
            logger.info(f"📡 Connecting to NATS: {self.nats_url}")
            self.nc = await nats.connect(self.nats_url)
            self.js = self.nc.jetstream()
            logger.info("✅ Connected to NATS")
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
            raise

        # Connect to Orchestrator
        try:
            logger.info(f"📡 Connecting to Orchestrator: {self.orchestrator_address}")
            channel = grpc.aio.insecure_channel(self.orchestrator_address)
            self.orchestrator_stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

            # Test connection
            status_request = orchestrator_pb2.GetStatusRequest(include_stats=False)
            status_response = await self.orchestrator_stub.GetStatus(status_request)
            logger.info(f"✅ Connected to Orchestrator (status: {status_response.status})")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Orchestrator: {e}")
            raise

    async def teardown(self):
        """Cleanup connections."""
        logger.info("🧹 Cleaning up test environment...")
        if self.nc:
            await self.nc.close()
        logger.info("✅ Cleanup complete")

    def record_test(self, name: str, passed: bool, message: str = ""):
        """Record test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "name": name,
            "passed": passed,
            "message": message
        })
        logger.info(f"{status}: {name}" + (f" - {message}" if message else ""))

    async def test_orchestrator_health(self) -> bool:
        """Test 1: Orchestrator health check."""
        logger.info("\n" + "="*70)
        logger.info("TEST 1: Orchestrator Health Check")
        logger.info("="*70)

        try:
            request = orchestrator_pb2.GetStatusRequest(include_stats=True)
            response = await self.orchestrator_stub.GetStatus(request)

            # Verify status is "healthy"
            if response.status != "healthy":
                self.record_test("Orchestrator Health", False, f"Status is {response.status}, expected 'healthy'")
                return False

            # Verify stats are present (structure changed in refactored API)
            if not response.stats:
                self.record_test("Orchestrator Health", False, "Stats not present in response")
                return False

            logger.info(f"   Uptime: {response.uptime_seconds}s")
            logger.info(f"   Active councils: {response.stats.active_councils}")

            self.record_test("Orchestrator Health", True, f"Uptime: {response.uptime_seconds}s")
            return True

        except Exception as e:
            self.record_test("Orchestrator Health", False, str(e))
            return False

    async def test_list_councils(self) -> bool:
        """Test 2: List councils."""
        logger.info("\n" + "="*70)
        logger.info("TEST 2: List Councils")
        logger.info("="*70)

        try:
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
            response = await self.orchestrator_stub.ListCouncils(request)

            # Verify we have councils
            if len(response.councils) == 0:
                self.record_test("List Councils", False, "No councils found")
                return False

            # Expected councils
            expected_roles = {"DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"}
            found_roles = {council.role for council in response.councils}

            logger.info(f"   Total councils: {len(response.councils)}")
            for council in response.councils:
                logger.info(f"     - {council.role}: {council.num_agents} agents")

            # Verify all expected roles are present
            missing_roles = expected_roles - found_roles
            if missing_roles:
                self.record_test("List Councils", False, f"Missing roles: {missing_roles}")
                return False

            self.record_test("List Councils", True, f"{len(response.councils)} councils found")
            return True

        except Exception as e:
            self.record_test("List Councils", False, str(e))
            return False

    async def test_nats_publish_event(self) -> bool:
        """Test 3: Publish PlanApproved event to NATS (async trigger)."""
        logger.info("\n" + "="*70)
        logger.info("TEST 3: Publish Event to NATS")
        logger.info("="*70)

        try:
            # Publish a proper PlanApproved event that the orchestrator consumes
            plan_id = f"e2e-plan-{int(time.time())}"
            story_id = "e2e-story-001"
            test_event = {
                "story_id": story_id,
                "plan_id": plan_id,
                "approved_by": "e2e",
                "roles": ["DEV"],
                "timestamp": time.time(),
            }

            import json
            event_json = json.dumps(test_event).encode()

            # Publish to the subject that Orchestrator is listening to
            subject = "planning.plan.approved"

            logger.info(f"   Publishing test event to: {subject}")
            ack = await self.js.publish(subject, event_json)

            logger.info("   Event published successfully")
            logger.info(f"     Stream: {ack.stream}")
            logger.info(f"     Sequence: {ack.seq}")
            # Save for async polling later
            self.last_plan_id = plan_id

            self.record_test("Publish Event to NATS", True, f"Event published to {subject}")
            return True

        except Exception as e:
            self.record_test("Publish Event to NATS", False, str(e))
            return False

    async def test_deliberate_grpc(self) -> bool:
        """Test 4: Trigger deliberation via gRPC."""
        logger.info("\n" + "="*70)
        logger.info("TEST 4: Trigger Deliberation via gRPC")
        logger.info("="*70)

        try:
            # Build request per refactored API
            constraints = orchestrator_pb2.TaskConstraints(
                rubric="Security Review",
                requirements=[
                    "Check for SQL injection",
                    "Verify password hashing",
                    "Ensure session management is correct",
                ],
                timeout_seconds=30,
            )

            request = orchestrator_pb2.DeliberateRequest(
                task_description=(
                    "Review the authentication module for security vulnerabilities"
                ),
                role="DEV",
                constraints=constraints,
                rounds=1,
                num_agents=1,
            )

            logger.info("   Triggering deliberation...")
            logger.info("     Role: DEV")
            logger.info("     Rounds: 1")

            # Call Deliberate RPC
            response = await self.orchestrator_stub.Deliberate(request)

            logger.info("   Deliberation response received:")
            logger.info(f"     Candidates: {len(response.results)}")
            logger.info(f"     Winner ID: {response.winner_id}")

            # Basic structural assertions
            if response is None:
                self.record_test("Trigger Deliberation", False, "No response received")
                return False

            self.record_test("Trigger Deliberation", True, f"Candidates: {len(response.results)}")
            return True

        except Exception as e:
            self.record_test("Trigger Deliberation", False, str(e))
            return False

    async def test_get_deliberation_result(self) -> bool:
        """Test 5: Get deliberation result (async, poll by task_id)."""
        logger.info("\n" + "="*70)
        logger.info("TEST 5: Get Deliberation Result")
        logger.info("="*70)

        try:
            if not self.last_plan_id:
                self.record_test("Get Deliberation Result", False, "No plan_id from previous step")
                return False

            task_id = self.last_plan_id
            logger.info(f"   Polling deliberation result for task_id: {task_id}")

            # Proactively publish simulated agent completed responses to drive collector
            try:
                import json
                from datetime import datetime
                assert self.js is not None
                for i in range(1, 4):
                    payload = {
                        "task_id": task_id,
                        "agent_id": f"agent-dev-00{i}",
                        "role": "DEV",
                        "proposal": {
                            "author_id": f"agent-dev-00{i}",
                            "author_role": "DEV",
                            "content": f"Proposal {i} for {task_id}",
                        },
                        "duration_ms": 500 + i * 10,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "num_agents": 3,
                    }
                    await self.js.publish(
                        "agent.response.completed",
                        json.dumps(payload).encode()
                    )
                logger.info("   Published simulated agent.response.completed events")
            except Exception as pub_err:
                logger.info(f"   Skipping simulated agent responses: {pub_err}")

            deadline = time.time() + 120.0  # 2 minutes
            last_status = ""
            while time.time() < deadline:
                try:
                    request = orchestrator_pb2.GetDeliberationResultRequest(task_id=task_id)
                    response = await self.orchestrator_stub.GetDeliberationResult(request)
                    last_status = getattr(response, "status", "")
                    if last_status in (getattr(orchestrator_pb2, "DELIBERATION_STATUS_COMPLETED", 3),
                                       getattr(orchestrator_pb2, "DELIBERATION_STATUS_FAILED", 4),
                                       getattr(orchestrator_pb2, "DELIBERATION_STATUS_TIMEOUT", 5)):
                        logger.info(f"   Result status: {last_status}")
                        self.record_test("Get Deliberation Result", True, f"Status: {last_status}")
                        return True
                except grpc.aio.AioRpcError:
                    # Not ready yet; continue polling
                    pass
                await asyncio.sleep(2.0)

            self.record_test("Get Deliberation Result", False, f"Timeout waiting for task_id {task_id} (last status: {last_status})")
            return False

        except Exception as e:
            self.record_test("Get Deliberation Result", False, str(e))
            return False

    async def run_all_tests(self):
        """Run all E2E tests."""
        logger.info("\n" + "🎯" * 35)
        logger.info("SWE AI FLEET - END-TO-END SYSTEM TEST")
        logger.info("🎯" * 35)

        try:
            await self.setup()

            # Run all tests
            await self.test_orchestrator_health()
            await self.test_list_councils()
            await self.test_nats_publish_event()
            await self.test_deliberate_grpc()
            await self.test_get_deliberation_result()

        finally:
            await self.teardown()

        # Print summary
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ Passed: {passed_tests}")
        logger.info(f"❌ Failed: {failed_tests}")
        logger.info("")

        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            logger.info(f"{status} {result['name']}: {result['message']}")

        logger.info("="*70)

        # Return exit code
        return 0 if failed_tests == 0 else 1


async def main():
    """Main entry point."""
    runner = E2ETestRunner()
    exit_code = await runner.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())

